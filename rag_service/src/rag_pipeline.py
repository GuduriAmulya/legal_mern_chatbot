import os
from typing import List, Optional, Dict
from groq import Groq
from .document_processor import DocumentProcessor
from .vector_store import VectorStore
from .conversation_manager import ConversationManager
from .legal_evaluator import LegalEvaluationManager
from .hybrid_retriever import HybridRetriever
import re

class RAGPipeline:
    def __init__(self, groq_api_key: str, index_dir: Optional[str] = None, mongo_uri: Optional[str] = None, db_name: Optional[str] = None):
        self.groq_client = Groq(api_key=groq_api_key)
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore(index_dir=index_dir)
        self.conversation_manager = ConversationManager(mongo_uri=mongo_uri, db_name=db_name)
        # evaluator optional
        try:
            self.evaluator = LegalEvaluationManager(self.groq_client)
        except Exception:
            self.evaluator = None
        self.is_initialized = False
        # token limits (model & reserved for response)
        self.model_max_tokens = int(os.getenv("MODEL_MAX_TOKENS", "6000"))
        self.reserved_response_tokens = int(os.getenv("RESERVED_RESPONSE_TOKENS", "1000"))
        # safe minimum k
        self.min_k = 1
        self.hybrid_retriever = None  # Initialize after documents loaded

    def initialize(self, data_folder: str, force_rebuild: bool = False):
        vector_dir = self.vector_store.index_dir
        loaded = False
        if not force_rebuild:
            loaded = self.vector_store.load()
        if loaded:
            print("Loaded existing vector store.")
        else:
            chunks = self.document_processor.process_documents(data_folder)
            if not chunks:
                raise RuntimeError("No documents found in data folder")
            print(f"Processing {len(chunks)} chunks")
            self.vector_store.add_documents(chunks)
            self.vector_store.save()
            print("Vector store built and saved.")
        
        # Initialize hybrid retriever after vector store is ready
        if self.vector_store.documents:
            try:
                self.hybrid_retriever = HybridRetriever(self.vector_store, self.vector_store.documents)
                print("Hybrid retriever initialized.")
            except Exception as e:
                print(f"Hybrid retriever failed: {e}, falling back to vector-only")
                self.hybrid_retriever = None
        
        self.is_initialized = True

    def retrieve_context(self, query: str, k: int = 3) -> str:
        if not self.is_initialized:
            return ""
        
        # Use hybrid search if available, else fallback to vector-only
        if self.hybrid_retriever:
            print(f"DEBUG: Using HYBRID retrieval for query: {query[:50]}...")  # ← Add this
            results = self.hybrid_retriever.search(query, k, alpha=0.9)  # ← Try 90% vector, 10% BM25 first
        else:
            print(f"DEBUG: Using VECTOR-ONLY retrieval for query: {query[:50]}...")  # ← Add this
            results = self.vector_store.search(query, k)
        
        context_parts = [doc for doc, score in results if score > 0.2]
        # fallback take top-k even if low score
        if not context_parts and results:
            context_parts = [doc for doc, score in results[:k]]
        return "\n\n".join(context_parts)

    def _estimate_tokens(self, text: str) -> int:
        """Same heuristic as ConversationManager (1 token ≈ 4 chars)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def is_greeting(self, query: str) -> bool:
        if not query:
            return False
        q = query.strip().lower()
        
        # Very short single-word greetings
        if len(q.split()) == 1 and q in ['hi', 'hey', 'hello', 'yo', 'thanks', 'thx', 'bye']:
            return True
        
        # Short polite phrases (2 words max)
        if len(q.split()) <= 2:
            greeting_patterns = ['good morning', 'good night', 'good evening', 'thank you', 'thanks a lot']
            if q in greeting_patterns:
                return True
        
        return False

    def is_informational(self, query: str) -> bool:
        """Heuristic: treat as informational if it's a question, long, or contains legal keywords."""
        if not query:
            return False
        q = query.strip().lower()
        if "?" in q:
            return True
        if len(q) > 40:
            return True
        legal_keywords = [
            "article", "section", "act", "law", "rights", "ipc", "judgment", "judgement",
            "court", "statute", "contract", "evidence", "penalty", "fine", "offence", "crime",
            "liable", "liability", "divorce", "marriage", "custody", "writ", "injunction"
        ]
        for kw in legal_keywords:
            if kw in q:
                return True
        return False

    def generate_response(self, query: str, context: str, conversation_context: str = "") -> str:
        system_prompt = """You are a helpful legal assistant specializing in human rights law.
Use the provided context to answer questions accurately and cite relevant information when possible.
If the context doesn't contain relevant information, say so clearly."""
        user_prompt = f"Conversation:\n{conversation_context}\n\nContext:\n{context}\n\nQuestion: {query}"
        try:
            resp = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"LLM error: {e}")
            return f"Error generating response: {e}"

    def rewrite_query_with_context(self, query: str, conversation_context: str) -> str:
        """Rewrite ambiguous follow-up queries using conversation context."""
        if not conversation_context or len(query.split()) > 15:
            return query

        follow_up_keywords = ["that", "this", "those", "it", "them", "examples", "more", "explain", "elaborate", "tell me"]
        if not any(kw in query.lower() for kw in follow_up_keywords):
            return query

        rewrite_prompt = f"""Previous conversation:
{conversation_context[-800:]}

User's follow-up question: {query}

Rewrite the user's question to be self-contained by incorporating relevant context. Keep it concise.
Rewritten question:"""

        try:
            resp = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": rewrite_prompt}],
                temperature=0.1,
                max_tokens=60
            )
            rewritten = resp.choices[0].message.content.strip()
            print(f"DEBUG: Query rewritten from '{query}' to '{rewritten}'")
            return rewritten
        except Exception:
            return query

    def chat(self, session_id: str, query: str, include_history: bool = True, evaluate: bool = False) -> Dict:
        """Chat with turn-by-turn summarization and query rewriting for follow-ups."""
        # If the query is non-informational (greeting/chit-chat), skip retrieval entirely.
        if self.is_greeting(query) and not self.is_informational(query):
            print(f"DEBUG: Skipping retrieval for greeting: '{query[:120]}' (session {session_id})")
            response_text = self.generate_response(query, context="", conversation_context="")
            debug = {
                "conversation_context_preview": "",
                "retrieved_context_preview": "",
                "tokens_estimate": {
                    "conversation": 0,
                    "retrieved": 0,
                    "query": self._estimate_tokens(query),
                    "total_context_allowed": self.model_max_tokens - self.reserved_response_tokens
                },
                "used_k": 0,
                "note": "retrieval_skipped_greeting"
            }

            try:
                self.conversation_manager.messages.insert_one({
                    "session_id": session_id,
                    "sender": "user",
                    "text": query,
                    "created_at": __import__("datetime").datetime.utcnow(),
                    "debug": {"note": "greeting_user_input"}
                })
                self.conversation_manager.messages.insert_one({
                    "session_id": session_id,
                    "sender": "assistant",
                    "text": response_text,
                    "created_at": __import__("datetime").datetime.utcnow(),
                    "debug": debug
                })
            except Exception:
                pass

            evaluation = None
            if evaluate and self.evaluator:
                try:
                    evaluation = self.evaluator.evaluate_conversation_turn(session_id, query, response_text, context="")
                except Exception as e:
                    print(f"Evaluation failed for greeting: {e}")

            return {"response": response_text, "debug": debug, "evaluation": evaluation}

        # Informational query - full RAG flow
        desired_k = int(os.getenv("RETRIEVE_K", "5"))
        k = desired_k

        conversation_context = self.conversation_manager.get_conversation_context(
            session_id,
            groq_client=self.groq_client if include_history else None
        ) if include_history else ""

        original_query = query
        if include_history and conversation_context:
            query = self.rewrite_query_with_context(query, conversation_context)

        available_context_tokens = max(256, self.model_max_tokens - self.reserved_response_tokens)
        query_tokens = self._estimate_tokens(query)

        retrieved_context = ""
        while True:
            retrieved_context = self.retrieve_context(query, k)
            tokens_total = (
                self._estimate_tokens(conversation_context)
                + self._estimate_tokens(retrieved_context)
                + query_tokens
            )

            if tokens_total <= available_context_tokens:
                break

            if include_history and self.groq_client:
                try:
                    self.conversation_manager.ensure_summary_limit(session_id, self.groq_client, max_summary_tokens=500)
                    conversation_context = self.conversation_manager.get_conversation_context(session_id, groq_client=None)
                    tokens_total = (
                        self._estimate_tokens(conversation_context)
                        + self._estimate_tokens(retrieved_context)
                        + query_tokens
                    )
                    if tokens_total <= available_context_tokens:
                        break
                except Exception:
                    pass

            if k > self.min_k:
                k = max(self.min_k, k - 1)
                continue

            allowed_tokens_for_retrieved = max(0, available_context_tokens - self._estimate_tokens(conversation_context) - query_tokens)
            if allowed_tokens_for_retrieved <= 0:
                conv_chars_keep = max(0, (available_context_tokens // 2) * 4)
                conversation_context = (conversation_context[-conv_chars_keep:]) if conv_chars_keep > 0 else ""
                allowed_tokens_for_retrieved = max(0, available_context_tokens - self._estimate_tokens(conversation_context) - query_tokens)

            char_limit = allowed_tokens_for_retrieved * 4
            if char_limit < len(retrieved_context):
                retrieved_context = retrieved_context[:char_limit]
            break

        try:
            print("\n" + "="*80)
            print(f"DEBUG: SESSION_ID: {session_id}")
            print("="*80)
            print(f"DEBUG: Conversation context length: {len(conversation_context)} chars")
            if conversation_context:
                print("DEBUG: Conversation context preview:")
                print(conversation_context[:1000])
            print("-"*80)
            print(f"DEBUG: Retrieved context length: {len(retrieved_context)} chars (using k={k})")
            if retrieved_context:
                print("DEBUG: Retrieved context preview:")
                print(retrieved_context[:1000])
            print("="*80 + "\n")
        except Exception as e:
            print(f"DEBUG: Failed to print debug context: {e}")

        response_text = self.generate_response(query, retrieved_context, conversation_context)

        try:
            print("\n" + "="*80)
            print(f"DEBUG: GENERATED RESPONSE (session {session_id}) - preview:")
            print(response_text[:2000])
            print("="*80 + "\n")
        except Exception:
            pass

        debug = {
            "conversation_context_preview": conversation_context[:1000],
            "retrieved_context_preview": retrieved_context[:2000],
            "tokens_estimate": {
                "conversation": self._estimate_tokens(conversation_context),
                "retrieved": self._estimate_tokens(retrieved_context),
                "query": query_tokens,
                "total_context_allowed": available_context_tokens
            },
            "used_k": k,
            "query_rewritten": query != original_query,
            "original_query": original_query if original_query != query else None,
            "rewritten_query": query if original_query != query else None
        }

        if include_history:
            self.conversation_manager.add_exchange(
                session_id, query, response_text,
                debug={"assistant": debug},
                groq_client=self.groq_client
            )
        else:
            self.conversation_manager.messages.insert_one({
                "session_id": session_id,
                "sender": "user",
                "text": query,
                "created_at": __import__("datetime").datetime.utcnow(),
                "debug": {"retrieved_context_preview": retrieved_context[:500]}
            })
            self.conversation_manager.messages.insert_one({
                "session_id": session_id,
                "sender": "assistant",
                "text": response_text,
                "created_at": __import__("datetime").datetime.utcnow(),
                "debug": debug
            })

        evaluation = None
        if evaluate and self.evaluator:
            try:
                evaluation = self.evaluator.evaluate_conversation_turn(
                    session_id, 
                    query, 
                    response_text,
                    context=retrieved_context
                )
                if evaluation and not isinstance(evaluation, dict):
                    evaluation = None
            except Exception as e:
                print(f"Evaluation failed: {e}")
                evaluation = None

        return {
            "response": response_text,
            "debug": debug,
            "evaluation": evaluation
        }
