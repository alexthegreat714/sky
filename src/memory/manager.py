from pathlib import Path
import json, time
from typing import Dict, Any, List

BASE = Path(__file__).resolve().parents[1].parent  # repo root
MEM_DIR = BASE / "memory"
MEM_DIR.mkdir(exist_ok=True, parents=True)
ST_FILE = MEM_DIR / "short_term.jsonl"
LT_FILE = MEM_DIR / "long_term.jsonl"  # for compatibility/export; Chroma holds embeddings

def _append_jsonl(path: Path, rec: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def remember_short(content: str, tags: List[str] = None, importance: float = 0.4):
    rec = {"ts": time.time(), "type": "short", "content": content, "tags": tags or [], "importance": importance}
    _append_jsonl(ST_FILE, rec)
    return rec

def remember_long_export(content: str, tags: List[str] = None, importance: float = 0.8):
    """Export plain record for long-term archival; embedding stored via Chroma in src/rag/."""
    rec = {"ts": time.time(), "type": "long", "content": content, "tags": tags or [], "importance": importance}
    _append_jsonl(LT_FILE, rec)
    return rec
