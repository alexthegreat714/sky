# Sky RAG Index

This directory contains Sky's vector embeddings index for long-term memory retrieval.

## Purpose

The RAG (Retrieval-Augmented Generation) system allows Sky to:
- Query her own long-term memories
- Retrieve relevant context for decision-making
- Answer questions about past events
- Maintain continuity across sessions

## Structure (Phase 2)

When implemented, this directory will contain:
- Vector embeddings database
- Metadata mappings
- Index configuration
- Cache files

## Usage

Sky automatically queries this index when asked about past events or when context is needed for tool decisions.

## Maintenance

The index is rebuilt by running:
```bash
python rag/ingest.py
```

This reads from `memory/long_term.jsonl` and builds fresh embeddings.

## Implementation Status

**Current:** Stub implementation (directory structure only)
**Phase 2:** Full vector DB integration with embedding model
