"""
Hobbs Inbox - Consumes messages from Senate Bus

Listens for messages on specific topics and stores them in Hobbs's memory
"""
from pathlib import Path
import json
import time
from typing import List, Dict, Any

BASE = Path(__file__).resolve().parents[3]  # repo root
HOBBS_DIR = BASE / "src" / "agents" / "hobbs"
HOBBS_MEMORY_DIR = HOBBS_DIR / "memory"
HOBBS_ST_FILE = HOBBS_MEMORY_DIR / "short_term.jsonl"
STATUS_DIR = BASE / "status"
STATUS_FILE = STATUS_DIR / "hobbs_last_msg.json"

def _append_jsonl(path: Path, rec: Dict[str, Any]):
    """Append single record to JSONL file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def _write_json(path: Path, data: Dict[str, Any]):
    """Write JSON file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def consume_messages(topics: List[str] = None) -> Dict[str, Any]:
    """
    Consume messages from Senate Bus and store in Hobbs memory

    Args:
        topics: List of topics to consume (default: ["daily.data_ready"])

    Returns:
        {
            "ok": bool,
            "consumed": int,
            "topics": [topic, ...]
        }
    """
    if topics is None:
        topics = ["daily.data_ready"]

    try:
        from src.senate_bus.broker import read_messages
    except Exception:
        return {"ok": False, "error": "Senate bus not available"}

    consumed_count = 0
    last_message = None

    for topic in topics:
        messages = read_messages(topic_filter=topic)

        for msg in messages:
            # Store in Hobbs's short-term memory
            memory_entry = {
                "ts": time.time(),
                "type": "short",
                "content": f"Senate message: {msg.get('payload', {})}",
                "tags": ["senate", topic],
                "importance": 0.6,  # Medium importance for inter-agent messages
                "source": "senate_bus",
                "original_message": msg
            }

            _append_jsonl(HOBBS_ST_FILE, memory_entry)
            consumed_count += 1
            last_message = msg

    # Log last message to status
    if last_message:
        status = {
            "ts": time.time(),
            "action": "message_consumed",
            "detail": {
                "topic": last_message.get("topic"),
                "payload": last_message.get("payload"),
                "consumed_count": consumed_count
            }
        }
        _write_json(STATUS_FILE, status)

    return {
        "ok": True,
        "consumed": consumed_count,
        "topics": topics
    }

def consume_once(topic: str = "daily.data_ready") -> Dict[str, Any]:
    """
    Convenience wrapper - consume messages from a single topic

    Args:
        topic: Topic to consume (default: "daily.data_ready")

    Returns:
        Result dict from consume_messages()
    """
    return consume_messages(topics=[topic])
