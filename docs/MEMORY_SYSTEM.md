# Memory System (Hybrid)
- Short-term: JSONL (append-only), easy to inspect and rotate.
- Long-term: vector store (Chroma). Ingestion/recall via src/rag/.
- Promotion: simple threshold in retention_rules.yaml (Phase 3 scaffold).
