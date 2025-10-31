import os
import pickle
from typing import List, Tuple
import numpy as np

from sentence_transformers import SentenceTransformer
import faiss

class VectorStore:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", index_dir: str = None):
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
        self.index = None
        self.documents: List[str] = []
        self.index_dir = index_dir or os.path.join(os.path.dirname(__file__), "..", "vector_store")
        os.makedirs(self.index_dir, exist_ok=True)
        self.index_path = os.path.join(self.index_dir, "faiss.index")
        self.pickle_path = os.path.join(self.index_dir, "docs.pkl")

    def add_documents(self, docs: List[str]):
        if not docs:
            return
        embeddings = self.model.encode(docs, convert_to_numpy=True, show_progress_bar=True)
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dim)
        # normalize for cosine via inner product
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.documents.extend(docs)

    def save(self):
        if self.index is not None:
            faiss.write_index(self.index, self.index_path)
        with open(self.pickle_path, "wb") as f:
            pickle.dump(self.documents, f)

    def load(self) -> bool:
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.pickle_path):
                self.index = faiss.read_index(self.index_path)
                with open(self.pickle_path, "rb") as f:
                    self.documents = pickle.load(f)
                return True
        except Exception as e:
            print(f"Failed to load vector store: {e}")
        return False

    def search(self, query: str, k: int = 3) -> List[Tuple[str, float]]:
        if self.index is None or len(self.documents) == 0:
            return []
        q_emb = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(q_emb)
        D, I = self.index.search(q_emb, k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx < len(self.documents):
                results.append((self.documents[idx], float(score)))
        return results
