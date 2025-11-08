# Sky Memory Promotion Engine

## Overview

Sky's memory system uses a three-tier architecture:
1. **Short-term** (JSONL) - Recent, ephemeral memories
2. **Long-term** (JSONL) - Important memories worthy of retention
3. **RAG Store** (ChromaDB) - Vectorized embeddings for semantic search

The **Memory Promotion Engine** automatically manages the flow from short → long → RAG based on importance thresholds.

---

## How It Works

### Scheduled Execution

The promoter runs every 10 minutes via the orchestrator:

**Schedule:** `src/sky/schedule.yaml`
```yaml
every:
  - name: "memory_rotate_check"
    minutes: 10
```

**Handler:** `src/sky/orchestrator.py`
```python
if name == "memory_rotate_check":
    result = memory_promoter_run()
    write_last_action("memory_rotate_check", result)
```

---

## Promotion Logic

### Threshold-Based Promotion

**Configuration:** `src/memory/retention_rules.yaml`
```yaml
promote_threshold: 0.70      # Minimum importance to promote
short_term_max_lines: 5000   # Maximum short-term entries before rotation
```

### Promotion Pipeline

For each entry in `memory/short_term.jsonl`:

1. **Load entry**
   ```json
   {
     "ts": 1699999999.123,
     "type": "short",
     "content": "User asked about Garmin sleep data",
     "tags": ["garmin", "sleep"],
     "importance": 0.85
   }
   ```

2. **Check threshold**
   - If `importance >= promote_threshold` (0.70):
     - **YES** → Promote to long-term + RAG
     - **NO** → Keep in short-term

3. **Promote**
   - Write to `memory/long_term.jsonl` with `promoted_at` timestamp
   - Pass content to RAG for embedding (Phase 3b+)
   - Remove from short-term

4. **Rotate**
   - If `len(short_term) > short_term_max_lines`:
     - Archive oldest entries to `memory/short_term_archive_{timestamp}.jsonl`
     - Keep only most recent `short_term_max_lines` entries

---

## Example Promotion Flow

### Before Promotion

**memory/short_term.jsonl:**
```jsonl
{"ts": 1699999990, "type": "short", "content": "trivial note", "importance": 0.3}
{"ts": 1699999995, "type": "short", "content": "important insight", "importance": 0.85}
{"ts": 1700000000, "type": "short", "content": "critical decision", "importance": 0.92}
```

### After Promotion (threshold = 0.70)

**memory/short_term.jsonl:**
```jsonl
{"ts": 1699999990, "type": "short", "content": "trivial note", "importance": 0.3}
```

**memory/long_term.jsonl:**
```jsonl
{"ts": 1699999995, "type": "long", "content": "important insight", "importance": 0.85, "promoted_at": 1700000100}
{"ts": 1700000000, "type": "long", "content": "critical decision", "importance": 0.92, "promoted_at": 1700000100}
```

**RAG Store (ChromaDB):**
- Embedded: "important insight"
- Embedded: "critical decision"

---

## How RAG Stores Are Updated

### Phase 3 (Current - Scaffold)

**Implementation:** `src/memory/promoter.py`
```python
def _safe_ingest_to_rag(content_list: List[str]):
    """Pass promoted content to RAG for embedding"""
    try:
        from src.rag.shared_ingest import ingest_paths
        ingest_paths(content_list)
    except Exception:
        pass  # RAG not available yet
```

**Current behavior:**
- Promoter calls `ingest_paths()` with content list
- `src/rag/shared_ingest.py` is a stub (prints message)
- No actual embedding occurs yet

### Phase 3b+ (Future Implementation)

**Enhanced implementation:**
```python
def _safe_ingest_to_rag(content_list: List[str]):
    """Embed promoted content into ChromaDB"""
    import chromadb
    from sentence_transformers import SentenceTransformer

    client = chromadb.PersistentClient(path="rag/chroma_store")
    collection = client.get_or_create_collection("sky_memory")

    model = SentenceTransformer('all-MiniLM-L6-v2')

    for idx, content in enumerate(content_list):
        embedding = model.encode(content)
        collection.add(
            embeddings=[embedding.tolist()],
            documents=[content],
            ids=[f"promoted_{int(time.time())}_{idx}"]
        )
```

**Vector retrieval:**
```python
def recall_similar(query: str, top_k: int = 5):
    """Semantic search over promoted memories"""
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    return results['documents'][0]
```

---

## Importance Scoring

### How Importance Is Assigned

When creating memories, agents assign importance scores (0.0 - 1.0):

**Low importance (0.0 - 0.5):**
- Routine status updates
- Transient user interactions
- Debugging logs

**Medium importance (0.5 - 0.7):**
- User preferences
- Scheduled task results
- Normal tool executions

**High importance (0.7 - 1.0):**
- Critical decisions
- User goals/intents
- System configurations
- Error patterns
- Important insights

### Example Usage

```python
from src.memory.manager import remember_short

# Low importance - transient
remember_short("User said hello", tags=["greeting"], importance=0.3)

# High importance - promoted to RAG
remember_short(
    "User wants daily Garmin reports at 7am with TTS",
    tags=["garmin", "preference", "schedule"],
    importance=0.9
)
```

---

## Rotation Behavior

### When Rotation Occurs

If `memory/short_term.jsonl` exceeds `short_term_max_lines` (default: 5000):

1. **Archive oldest entries**
   - Create `memory/short_term_archive_{timestamp}.jsonl`
   - Move oldest entries to archive

2. **Keep recent entries**
   - Retain only most recent `short_term_max_lines` entries
   - Write back to `memory/short_term.jsonl`

### Archive Access

Archived memories are not lost - they can be manually searched:

```bash
# Find old memory in archives
grep "garmin" memory/short_term_archive_*.jsonl
```

Future versions may include archive search tools.

---

## Monitoring Promotion

### Status Updates

Every promotion run updates `status/sky_last_action.json`:

```json
{
  "ts": 1700000100.456,
  "action": "memory_rotate_check",
  "detail": {
    "ok": true,
    "promoted": 12,
    "rotated": false,
    "remaining": 247,
    "threshold": 0.7
  }
}
```

### Fields:
- `promoted`: Number of entries promoted to long-term + RAG
- `rotated`: Whether short-term was rotated (archived)
- `remaining`: Entries still in short-term
- `threshold`: Promotion threshold used

### Manual Promotion

Run promoter manually:

```python
from src.memory.promoter import run_once

result = run_once()
print(f"Promoted {result['promoted']} entries")
```

---

## Configuration Reference

### retention_rules.yaml

```yaml
# Minimum importance to promote to long-term + RAG
promote_threshold: 0.70

# Maximum short-term entries before rotation
short_term_max_lines: 5000
```

**Tuning recommendations:**
- **Higher threshold (0.8+)**: More selective, smaller RAG store, faster search
- **Lower threshold (0.5-0.7)**: More comprehensive, larger RAG store, richer recall
- **Default (0.7)**: Balanced - captures important insights without noise

---

## Future Enhancements (Phase 4+)

- [ ] **Smart importance scoring** - ML-based importance prediction
- [ ] **Time-decay promotion** - Lower threshold for older memories
- [ ] **Tag-based promotion** - Auto-promote specific tags (e.g., "critical", "user_goal")
- [ ] **Semantic deduplication** - Prevent redundant embeddings in RAG
- [ ] **Archive search tools** - Query archived memories
- [ ] **Memory consolidation** - Summarize related memories
- [ ] **Multi-agent memory sharing** - Selective memory sharing between Sky/Hobbs/Aegis
- [ ] **Memory expiration** - Auto-delete very old, low-importance memories
