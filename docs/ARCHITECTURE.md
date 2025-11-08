# RAG Architecture (Scaffold)
- Backend: Chroma (local folder DB at src/rag/chroma_store/)
- Ingest: src/rag/shared_ingest.py
- Query: src/rag/query.py
- Agents can keep their own per-agent stores under src/agents/<name>/memory/vector_index/
