import os
import re
from typing import List
from PyPDF2 import PdfReader

class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        text = ""
        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                for p in reader.pages:
                    page_text = p.extract_text() or ""
                    text += page_text + "\n"
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
        return text

    def clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def chunk_text(self, text: str) -> List[str]:
        words = text.split()
        if not words:
            return []
        chunks = []
        step = self.chunk_size - self.chunk_overlap
        for i in range(0, len(words), step):
            chunk = ' '.join(words[i:i + self.chunk_size])
            chunks.append(chunk)
            if i + self.chunk_size >= len(words):
                break
        return chunks

    def process_documents(self, data_folder: str) -> List[str]:
        """Process documents and return text chunks (plain strings for vector store)."""
        all_chunks = []
        if not os.path.exists(data_folder):
            return []
        for fname in os.listdir(data_folder):
            if fname.lower().endswith(".pdf"):
                path = os.path.join(data_folder, fname)
                print(f"Processing {fname}")
                text = self.extract_text_from_pdf(path)
                cleaned = self.clean_text(text)
                chunks = self.chunk_text(cleaned)
                # Return plain strings (not dicts) for compatibility with vector store and BM25
                all_chunks.extend(chunks)
        return all_chunks
