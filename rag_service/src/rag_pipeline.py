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
        # ✅ IMPROVED: More specific system prompt
        system_prompt = """You are a legal assistant specializing in Indian constitutional law and human rights.

Your knowledge domains:
- Indian Constitution (Articles, Amendments, Schedules)
- Fundamental Rights (Articles 12-35)
- Directive Principles of State Policy
- Universal Declaration of Human Rights (UDHR)
- Constitutional governance structures (Panchayati Raj, etc.)

Guidelines:
1. Always cite specific Articles/Sections when applicable
2. Distinguish between constitutional rights vs. human rights treaties
3. If context lacks relevant information, say: "Based on the available documents, I don't have specific information on this topic."
4. Use clear, accessible language while maintaining legal accuracy
"""
        
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
        """Intelligently rewrite ONLY true follow-up queries."""
        # ✅ RULE 1: Skip if no conversation history
        if not conversation_context:
            return query
        
        # ✅ RULE 2: Skip if query is already detailed (>15 words)
        if len(query.split()) > 15:
            return query
        
        # ✅ RULE 3: Skip if query starts with informational keywords (new topic)
        informational_starters = [
            'explain', 'what is', 'what are', 'what was', 'what does',
            'who', 'when', 'where', 'why', 'how', 'which',
            'define', 'describe', 'list', 'tell me about'
        ]
        if any(query.lower().strip().startswith(starter) for starter in informational_starters):
            print(f"DEBUG: Skipping rewrite - query starts with informational keyword")
            return query
        
        # ✅ RULE 4: Skip if query contains specific legal terms (likely standalone)
        specific_legal_terms = [
            'article', 'section', 'act', 'ipc', 'crpc', 'constitution',
            'amendment', 'schedule', 'panchayat', 'fundamental rights',
            'directive principles', 'udhr', 'iccpr'
        ]
        if any(term in query.lower() for term in specific_legal_terms):
            print(f"DEBUG: Skipping rewrite - query contains specific legal term")
            return query
        
        # ✅ RULE 5: Only rewrite if query has STRONG follow-up indicators
        strong_follow_up_patterns = [
            r'\bthat\b',           # "explain that"
            r'\bthis\b',           # "what about this"
            r'\bthose\b',          # "give those examples"
            r'\bit\b',             # "elaborate on it"
            r'\bthem\b',           # "list them"
            r'^(more|another)',    # starts with "more" or "another"
            r'^(give|show|provide)\s+(me\s+)?(examples?|details?)',  # "give examples"
        ]
        
        has_follow_up = any(re.search(pattern, query.lower()) for pattern in strong_follow_up_patterns)
        
        if not has_follow_up:
            print(f"DEBUG: Skipping rewrite - no strong follow-up indicators")
            return query
        
        # ✅ ONLY NOW do we attempt rewriting (high confidence it's a follow-up)
        print(f"DEBUG: Detected follow-up query, attempting rewrite...")
        
        rewrite_prompt = f"""You are rewriting a follow-up legal question to be self-contained.

Previous conversation (last 2 turns):
{conversation_context[-800:]}

User's follow-up: {query}

Rules:
1. If the query references "that", "this", "it", replace with the actual topic from conversation
2. Preserve exact legal terminology (Article numbers, act names, constitutional terms)
3. Keep it concise (max 20 words)
4. If already clear, return unchanged

Rewritten question:"""

        try:
            resp = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": rewrite_prompt}],
                temperature=0.05,  # ✅ Lower temp for more consistent rewrites
                max_tokens=50
            )
            rewritten = resp.choices[0].message.content.strip()
            
            # ✅ Safety check: if rewritten is too different (>2x length), use original
            if len(rewritten.split()) > len(query.split()) * 2:
                print(f"DEBUG: Rewrite too verbose, using original")
                return query
            
            print(f"DEBUG: Query rewritten from '{query}' to '{rewritten}'")
            return rewritten
            
        except Exception as e:
            print(f"DEBUG: Rewrite failed ({e}), using original")
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

        return {"response": response_text, "debug": debug, "evaluation": evaluation}