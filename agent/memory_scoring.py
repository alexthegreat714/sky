from pathlib import Path
import json, time

BASE = Path(__file__).resolve().parents[1]
MEM = BASE / "memory"
ST = MEM / "short_term.jsonl"
LT = MEM / "long_term.jsonl"
MEM.mkdir(exist_ok=True)

def _append_jsonl(path: Path, rec: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def decide_and_store(content: str, tags=None, importance: float = None):
    """
    If importance not provided, use simple heuristics now (LLM later):
      - >= 0.7 → long-term
      - else → short-term
    """
    tags = tags or []
    if importance is None:
        importance = 0.8 if any(k in content.lower() for k in ["policy","preference","persistent","recurring"]) else 0.4
    rec = {"ts": time.time(), "content": content, "tags": tags, "importance": importance}
    if importance >= 0.7:
        rec["type"] = "long"
        _append_jsonl(LT, rec)
        return {"stored":"long", "importance":importance}
    else:
        rec["type"] = "short"
        _append_jsonl(ST, rec)
        return {"stored":"short", "importance":importance}
