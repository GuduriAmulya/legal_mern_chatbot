import json
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

class LegalEvaluationManager:
    def __init__(self, groq_client):
        self.groq_client = groq_client
        mongo_uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
        dbname = os.getenv("MONGO_DB_NAME") or "rag_service"
        self.client = MongoClient(mongo_uri)
        self.db = self.client[dbname]
        self.coll = self.db.get_collection("evaluations")

    def evaluate_conversation_turn(self, session_id: str, query: str, response: str, context: str = ""):
        """Evaluate using query + retrieved context as reference (no gold answer needed)."""
        
        prompt = f"""You are an expert legal evaluation system. Assess the quality of this legal assistant's response using the query and retrieved legal context as reference.

**USER QUERY:**
{query}

**RETRIEVED LEGAL CONTEXT (Ground Truth):**
{context[:2000] if context else "No context provided"}

**AI RESPONSE TO EVALUATE:**
{response}

Evaluate on 5 dimensions (1-5 scale):

1. **FACTUAL ACCURACY** (1-5): Does the response accurately reflect the legal provisions in the context? Are facts correct?

2. **LEGAL REASONING** (1-5): Is the legal analysis logically sound? Are arguments well-structured?

3. **CITATION QUALITY** (1-5): Are legal sources (articles, acts) properly mentioned and attributed?

4. **CLARITY** (1-5): Is the language clear, professional, and understandable?

5. **COMPLETENESS** (1-5): Does it fully address all aspects of the user's query?

Respond in JSON:
{{
  "factual_accuracy": {{"score": X, "reason": "..."}},
  "legal_reasoning": {{"score": X, "reason": "..."}},
  "citation_quality": {{"score": X, "reason": "..."}},
  "clarity": {{"score": X, "reason": "..."}},
  "completeness": {{"score": X, "reason": "..."}},
  "overall_score": X.X,
  "summary": "Brief overall assessment"
}}
"""
        
        try:
            api_resp = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Use larger model for better judgment
                messages=[
                    {"role": "system", "content": "You are a legal evaluation expert. Always respond in valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            eval_json = {}
            try:
                eval_json = json.loads(api_resp.choices[0].message.content)
            except Exception as e:
                print(f"JSON parse error: {e}")
                eval_json = {"raw": api_resp.choices[0].message.content, "error": "parse_failed"}
            doc = {
                "session_id": session_id,
                "query": query,
                "response": response,
                "evaluation": eval_json,
                "timestamp": datetime.utcnow()
            }
            result = self.coll.insert_one(doc)
            
            # Convert ObjectId to string before returning
            doc['_id'] = str(result.inserted_id)
            # Remove MongoDB-specific fields that aren't JSON serializable
            serializable_doc = {
                "session_id": doc["session_id"],
                "query": doc["query"],
                "response": doc["response"],
                "evaluation": doc["evaluation"],
                "timestamp": doc["timestamp"].isoformat() if isinstance(doc["timestamp"], datetime) else str(doc["timestamp"])
            }
            return serializable_doc
        except Exception as e:
            print(f"Evaluation error: {e}")
            return None
