"""
Memory Promotion Engine - Manages short → long → RAG flow

Scans short_term.jsonl for high-importance entries:
- If importance >= promote_threshold → write to long_term.jsonl + RAG
- Rotates short_term.jsonl if > max_lines
"""
from pathlib import Path
import json
import shutil
import time
from typing import Dict, Any, List

BASE = Path(__file__).resolve().parents[2]  # repo root
MEM_DIR = BASE / "memory"
ST_FILE = MEM_DIR / "short_term.jsonl"
LT_FILE = MEM_DIR / "long_term.jsonl"
RULES_FILE = BASE / "src" / "memory" / "retention_rules.yaml"

def _load_retention_rules() -> Dict[str, Any]:
    """Load retention rules from YAML"""
    if not RULES_FILE.exists():
        return {"promote_threshold": 0.70, "short_term_max_lines": 5000}

    try:
        import yaml
        rules = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
        return rules or {}
    except Exception:
        return {"promote_threshold": 0.70, "short_term_max_lines": 5000}

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read all lines from JSONL file"""
    if not path.exists():
        return []

    entries = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    return entries

def _append_jsonl(path: Path, rec: Dict[str, Any]):
    """Append single record to JSONL file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def _write_jsonl(path: Path, entries: List[Dict[str, Any]]):
    """Overwrite JSONL file with entries"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in entries:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def _safe_ingest_to_rag(content_list: List[str]):
    """
    Pass promoted content to RAG for embedding
    (scaffold - actual embedding happens in Phase 3b)
    """
    try:
        from src.rag.shared_ingest import ingest_paths
        # For now, just call with content strings
        # In Phase 3b, this will embed to ChromaDB
        ingest_paths(content_list)
    except Exception:
        pass  # RAG not available yet

def promote_entries(entries: List[Dict[str, Any]], threshold: float) -> tuple[List[Dict], List[Dict]]:
    """
    Separate entries into promoted (importance >= threshold) and kept

    Returns:
        (promoted_entries, remaining_entries)
    """
    promoted = []
    remaining = []

    for entry in entries:
        importance = entry.get("importance", 0.0)
        if importance >= threshold:
            # Mark as promoted and add to long-term
            promoted_entry = {**entry, "type": "long", "promoted_at": time.time()}
            promoted.append(promoted_entry)
        else:
            remaining.append(entry)

    return promoted, remaining

def rotate_short_term(entries: List[Dict[str, Any]], max_lines: int) -> List[Dict[str, Any]]:
    """
    Rotate short_term.jsonl if > max_lines
    Keep only the most recent max_lines entries
    """
    if len(entries) <= max_lines:
        return entries

    # Archive old entries
    archive_file = MEM_DIR / f"short_term_archive_{int(time.time())}.jsonl"
    archived_count = len(entries) - max_lines
    _write_jsonl(archive_file, entries[:archived_count])

    # Return only recent entries
    return entries[-max_lines:]

def run_once() -> Dict[str, Any]:
    """
    Run memory promotion pipeline once

    Returns:
        {
            "ok": bool,
            "promoted": int,
            "rotated": bool,
            "remaining": int
        }
    """
    rules = _load_retention_rules()
    threshold = rules.get("promote_threshold", 0.70)
    max_lines = rules.get("short_term_max_lines", 5000)

    # Read short-term memory
    st_entries = _read_jsonl(ST_FILE)

    if not st_entries:
        return {"ok": True, "promoted": 0, "rotated": False, "remaining": 0}

    # Promote high-importance entries
    promoted, remaining = promote_entries(st_entries, threshold)

    # Write promoted entries to long-term
    promoted_content = []
    for entry in promoted:
        _append_jsonl(LT_FILE, entry)
        # Collect content for RAG embedding
        promoted_content.append(entry.get("content", ""))

    # Pass promoted content to RAG
    if promoted_content:
        _safe_ingest_to_rag(promoted_content)

    # Rotate if needed
    rotated = False
    if len(remaining) > max_lines:
        remaining = rotate_short_term(remaining, max_lines)
        rotated = True

    # Rewrite short-term with remaining entries
    _write_jsonl(ST_FILE, remaining)

    return {
        "ok": True,
        "promoted": len(promoted),
        "rotated": rotated,
        "remaining": len(remaining),
        "threshold": threshold
    }
