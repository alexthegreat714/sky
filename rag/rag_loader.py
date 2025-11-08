"""
Phase 3 RAG loader — scaffold only.

Will use Chroma or FAISS depending on config.
"""

def load_index():
    return None  # will be replaced in Phase 3b

def query_index(text: str, k: int = 4):
    return {"matches": [], "source_docs": []}
