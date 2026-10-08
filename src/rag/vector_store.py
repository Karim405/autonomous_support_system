"""
Vector Store Engine using FAISS & Sentence-Transformers (with resilient fallback):
- Indexes policy PDF and product catalog Excel
- Performs high-speed semantic search over company documents
- Stores index locally at data/faiss_index
"""

import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INDEX_DIR = os.path.join(BASE_DIR, "data", "faiss_index")
os.makedirs(INDEX_DIR, exist_ok=True)

INDEX_FILE = os.path.join(INDEX_DIR, "index.faiss")
METADATA_FILE = os.path.join(INDEX_DIR, "metadata.pkl")

class KnowledgeVectorStore:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.index = None
        self.documents: List[Dict[str, Any]] = []
        self._init_embedding_model()

    def _init_embedding_model(self):
        """Initializes SentenceTransformer or falls back cleanly."""
        try:
            from sentence_transformers import SentenceTransformer
            # Use local cache or download lightweight MiniLM
            self.model = SentenceTransformer(self.model_name)
            self.use_dense = True
        except Exception as e:
            print(f"[Warning] SentenceTransformer could not be loaded ({e}). Using TF-IDF semantic vector fallback.")
            self.use_dense = False
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.tfidf = TfidfVectorizer(stop_words='english')

    def build_index(self, documents: List[Dict[str, Any]]):
        """Builds and saves the vector index from documents."""
        self.documents = documents
        texts = [doc["content"] for doc in documents]

        if not texts:
            print("No documents to index.")
            return

        if self.use_dense:
            import faiss
            embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # Inner Product for cosine similarity on normalized vectors
            self.index.add(embeddings.astype(np.float32))
            faiss.write_index(self.index, INDEX_FILE)
        else:
            self.tfidf_matrix = self.tfidf.fit_transform(texts)

        with open(METADATA_FILE, "wb") as f:
            pickle.dump(self.documents, f)
        
        print(f" Knowledge Base Indexed: {len(documents)} chunks stored.")

    def load_index(self) -> bool:
        """Loads index from disk if available."""
        if not os.path.exists(METADATA_FILE):
            return False

        with open(METADATA_FILE, "rb") as f:
            self.documents = pickle.load(f)

        if self.use_dense and os.path.exists(INDEX_FILE):
            import faiss
            self.index = faiss.read_index(INDEX_FILE)
            return True
        elif not self.use_dense:
            texts = [doc["content"] for doc in self.documents]
            self.tfidf_matrix = self.tfidf.fit_transform(texts)
            return True
        return False

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Semantic search returning top-k matching documents with scores."""
        if not self.documents:
            if not self.load_index():
                return []

        if self.use_dense and self.index:
            query_vector = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
            scores, indices = self.index.search(query_vector.astype(np.float32), top_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.documents):
                    doc = dict(self.documents[idx])
                    doc["relevance_score"] = float(score)
                    results.append(doc)
            return results
        else:
            # Fallback cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            query_vec = self.tfidf.transform([query])
            sims = cosine_similarity(query_vec, self.tfidf_matrix)[0]
            top_indices = sims.argsort()[-top_k:][::-1]

            results = []
            for idx in top_indices:
                doc = dict(self.documents[idx])
                doc["relevance_score"] = float(sims[idx])
                results.append(doc)
            return results

# Singleton instance helper
_vector_store_instance = None

def get_vector_store() -> KnowledgeVectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = KnowledgeVectorStore()
        if not _vector_store_instance.load_index():
            from src.rag.document_loader import load_all_knowledge_documents
            docs = load_all_knowledge_documents()
            _vector_store_instance.build_index(docs)
    return _vector_store_instance
