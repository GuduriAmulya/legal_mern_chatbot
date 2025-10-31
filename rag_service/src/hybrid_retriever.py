from rank_bm25 import BM25Okapi
import numpy as np

class HybridRetriever:
    def __init__(self, vector_store, documents):
        self.vector_store = vector_store
        self.documents = documents
        # Tokenize docs for BM25
        tokenized = []
        for doc in documents:
            tokens = doc.lower().split()
            tokens = [t for t in tokens if len(t) > 1]  # Filter short tokens
            tokenized.append(tokens if tokens else ["empty"])
        
        self.bm25 = BM25Okapi(tokenized)
        print(f"DEBUG: BM25 initialized with {len(tokenized)} documents")
    
    def search(self, query: str, k: int = 5, alpha: float = 0.5):
        """Combine BM25 + Vector using Reciprocal Rank Fusion (RRF)."""
        query_tokens = query.lower().split()
        query_tokens = [t for t in query_tokens if len(t) > 1]
        
        if not query_tokens:
            print(f"DEBUG: Empty query tokens, using vector-only")
            return self.vector_store.search(query, k)
        
        # Get BM25 ranked results
        bm25_scores = self.bm25.get_scores(query_tokens)
        bm25_ranked = np.argsort(bm25_scores)[::-1]  # Descending order
        
        # Get Vector ranked results
        vector_results = self.vector_store.search(query, k=len(self.documents))
        vector_ranked = []
        for doc, score in vector_results:
            try:
                idx = self.documents.index(doc)
                vector_ranked.append(idx)
            except ValueError:
                pass
        
        # Reciprocal Rank Fusion (RRF)
        # Score(d) = sum(1 / (k + rank(d))) for each retrieval method
        rrf_k = 60  # Standard RRF constant
        rrf_scores = {}
        
        # Add BM25 ranks
        for rank, doc_idx in enumerate(bm25_ranked[:k*3]):  # Consider top-3k from BM25
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + (1 / (rrf_k + rank + 1))
        
        # Add Vector ranks (weighted by alpha)
        for rank, doc_idx in enumerate(vector_ranked[:k*3]):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + (alpha / (rrf_k + rank + 1))
        
        # Sort by RRF score
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        # DEBUG
        top_bm25_score = bm25_scores[bm25_ranked[0]] if len(bm25_ranked) > 0 else 0
        top_vector_score = vector_results[0][1] if vector_results else 0
        print(f"DEBUG: BM25_top={top_bm25_score:.4f}, Vector_top={top_vector_score:.4f}, RRF_alpha={alpha}")
        
        # Return top-k with RRF scores
        results = []
        for doc_idx, rrf_score in sorted_docs[:k]:
            if doc_idx < len(self.documents):
                results.append((self.documents[doc_idx], rrf_score))
        
        return results
