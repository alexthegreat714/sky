"""
Senate Bus Broker - Message passing between agents

Phase 3: Filesystem-backed message queue (bus/messages.jsonl)
Phase 4+: Upgrade to Redis/RabbitMQ for production
"""
from pathlib import Path
import json
import time
from typing import Any, Dict, List
from .message_types import ActionRequest, VotePacket

BASE = Path(__file__).resolve().parents[2]  # repo root
BUS_DIR = BASE / "bus"
BUS_FILE = BUS_DIR / "messages.jsonl"

def publish(topic: str, payload):
    """Legacy scaffold publish (prints to console)"""
    print(f"[bus] publish {topic}: {payload}")

def subscribe(topic: str):
    """Legacy scaffold subscribe (prints to console)"""
    print(f"[bus] subscribe to {topic} (scaffold)")

def publish_json(topic: str, payload: Dict[str, Any]):
    """
    Publish message to senate bus

    Appends to bus/messages.jsonl with format:
    {
        "ts": timestamp,
        "topic": "daily.data_ready",
        "payload": {...}
    }

    Args:
        topic: Message topic (e.g., "daily.data_ready", "task.completed")
        payload: Message payload (arbitrary JSON dict)
    """
    BUS_DIR.mkdir(parents=True, exist_ok=True)

    message = {
        "ts": time.time(),
        "topic": topic,
        "payload": payload
    }

    with BUS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(message, ensure_ascii=False) + "\n")

    return message

def read_messages(topic_filter: str = None) -> List[Dict[str, Any]]:
    """
    Read all messages from bus, optionally filtered by topic

    Args:
        topic_filter: If provided, only return messages matching this topic

    Returns:
        List of message dicts: [{ts, topic, payload}, ...]
    """
    if not BUS_FILE.exists():
        return []

    messages = []
    with BUS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if topic_filter is None or msg.get("topic") == topic_filter:
                    messages.append(msg)
            except Exception:
                continue

    return messages
