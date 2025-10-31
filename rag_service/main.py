import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv
import logging
from fastapi.responses import StreamingResponse

from src.rag_pipeline import RAGPipeline

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_service")

MONGO_URI = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Resolve RAG_DATA_FOLDER (allow relative path in .env like ./data)
_env_folder = os.getenv("RAG_DATA_FOLDER", None)
_default_folder = os.path.join(os.path.dirname(__file__), "data")  # ← Changed from ".." to current dir
if _env_folder:
    # if env value is absolute, use it; otherwise resolve relative to rag_service root (where main.py is)
    if os.path.isabs(_env_folder):
        RAG_DATA_FOLDER = _env_folder
    else:
        # Resolve relative to main.py location (rag_service folder)
        RAG_DATA_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), _env_folder))
else:
    RAG_DATA_FOLDER = os.path.abspath(_default_folder)

PORT = int(os.getenv("PORT", 8000))

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY must be set in .env")

app = FastAPI(title="Local RAG Service")

# instantiate pipeline (vector store will be initialized at startup)
rag = RAGPipeline(
    GROQ_API_KEY,
    index_dir=os.path.join(os.path.dirname(__file__), "..", "vector_store"),
    mongo_uri=MONGO_URI,
    db_name=os.getenv("MONGO_DB_NAME") or "rag_service"
)

# --- Initialize at startup so /initialize is not required ---
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting RAG initialization at startup...")
        logger.info(f"Resolved RAG_DATA_FOLDER = {RAG_DATA_FOLDER}")
        # list files for quick debug
        try:
            files = os.listdir(RAG_DATA_FOLDER)
            pdfs = [f for f in files if f.lower().endswith('.pdf')]
            logger.info(f"Files in RAG_DATA_FOLDER ({RAG_DATA_FOLDER}): {len(files)} total, {len(pdfs)} pdf(s) found")
            if pdfs:
                for p in pdfs[:20]:
                    logger.info(f" - {p}")
        except FileNotFoundError:
            logger.warning(f"RAG_DATA_FOLDER does not exist: {RAG_DATA_FOLDER}")
        except Exception as e:
            logger.warning(f"Could not list RAG_DATA_FOLDER contents: {e}")

        rag.initialize(RAG_DATA_FOLDER, force_rebuild=False)
        logger.info("RAG initialized successfully at startup.")
    except Exception as e:
        logger.exception("RAG initialization failed at startup. Service will continue running but RAG may be unavailable.")

class InitRequest(BaseModel):
    force_rebuild: bool = False

class SessionCreate(BaseModel):
    user_id: str = None
    title: str = "New Chat"

class ChatRequest(BaseModel):
    session_id: str
    user_id: str = None
    query: str
    include_history: bool = True
    evaluate: bool = False

@app.post("/initialize")
def initialize(req: InitRequest):
    try:
        rag.initialize(RAG_DATA_FOLDER, force_rebuild=req.force_rebuild)
        return {"status": "initialized", "data_folder": RAG_DATA_FOLDER}
    except Exception as e:
        logger.exception("Initialization failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions")
def create_session(req: SessionCreate):
    sid = rag.conversation_manager.create_session()
    return {"session_id": sid, "title": req.title}

@app.post("/chat")
def chat(req: ChatRequest):
    if not rag.is_initialized:
        raise HTTPException(status_code=400, detail="RAG not initialized")
    try:
        out = rag.chat(req.session_id, req.query, include_history=req.include_history, evaluate=req.evaluate)
        
        # Ensure all fields in 'out' are JSON-serializable
        # Convert any datetime objects to ISO strings
        if out.get("debug"):
            if "tokens_estimate" in out["debug"]:
                # tokens_estimate is already primitives (int), safe
                pass
        
        # If evaluation exists, ensure it's a plain dict (legal_evaluator already returns serializable dict)
        if out.get("evaluation") is not None:
            # Force convert to dict if needed (should already be dict from evaluator)
            if not isinstance(out["evaluation"], dict):
                logger.warning(f"Evaluation result is not a dict: {type(out['evaluation'])}")
                out["evaluation"] = None
        
        return out
    except Exception as e:
        logger.exception("Chat error")
        # Return JSON error instead of letting FastAPI return HTML 500
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    if not rag.is_initialized:
        raise HTTPException(status_code=400, detail="RAG not initialized")
    try:
        async def generate():
            resp = rag.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": req.query}],
                stream=True
            )
            for chunk in resp:
                if chunk.choices[0].delta.content:
                    yield f"data: {chunk.choices[0].delta.content}\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/reset")
def reset(session_id: str):
    try:
        rag.conversation_manager.reset_session(session_id)
        return {"status": "reset", "session_id": session_id}
    except Exception as e:
        logger.exception("Reset failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok", "initialized": rag.is_initialized}

@app.post("/evaluate/retrieval")
def evaluate_retrieval(req: dict):
    """Compare hybrid vs vector-only retrieval."""
    queries = req.get("queries", [])
    mode = req.get("mode", "both")
    
    results = []
    
    for query in queries:
        if mode == "both":
            # Hybrid retrieval
            hybrid_docs = []
            if rag.hybrid_retriever:
                hybrid_results = rag.hybrid_retriever.search(query, k=5)
                hybrid_docs = [{"text": doc, "score": float(score)} for doc, score in hybrid_results]
            
            # Vector-only retrieval
            vector_results = rag.vector_store.search(query, k=5)
            vector_docs = [{"text": doc, "score": float(score)} for doc, score in vector_results]
            
            results.append({
                "query": query,
                "hybrid_results": hybrid_docs,
                "vector_results": vector_docs
            })
        else:
            # Single mode
            docs = rag.retrieve_context(query, k=5)
            results.append({"query": query, "retrieved": docs[:500]})
    
    return results