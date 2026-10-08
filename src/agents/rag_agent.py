"""
Knowledge & RAG Agent (Session 4 & Session 7):
- Queries FAISS Vector Store for relevant policies and product catalog data
- Returns grounded, factual operational context
"""

from typing import Dict, Any, List
from src.rag.vector_store import get_vector_store

class RAGAgent:
    def __init__(self, top_k: int = 2):
        self.top_k = top_k
        self.vector_store = get_vector_store()

    def retrieve_context(self, query: str) -> Dict[str, Any]:
        """
        Retrieves top relevant passages from PDF policies and Excel catalog.
        """
        results = self.vector_store.search(query, top_k=self.top_k)
        
        context_snippets = []
        sources = []
        for r in results:
            context_snippets.append(r["content"])
            src = r["metadata"].get("source", "company_kb")
            if src not in sources:
                sources.append(src)

        combined_text = "\n\n".join(context_snippets) if context_snippets else "No specific policy document found."

        return {
            "query": query,
            "grounded_context": combined_text,
            "sources": sources,
            "raw_matches": results
        }
