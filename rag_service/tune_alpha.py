import json
from src.rag_pipeline import RAGPipeline
import os

groq_key = os.getenv("GROQ_API_KEY")
rag = RAGPipeline(groq_key)
rag.initialize("./data")

alphas = [0.3, 0.5, 0.7, 0.9]
results = {}

for alpha in alphas:
    # Modify hybrid_retriever alpha
    rag.hybrid_retriever.search = lambda q, k: rag.hybrid_retriever.search(q, k, alpha=alpha)
    
    # Run benchmark (simplified)
    # ... run same benchmark loop ...
    
    results[alpha] = accuracy

print(results)
# Expected: alpha=0.5-0.7 performs best
