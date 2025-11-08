"""
Tests for Senate Bus message flow (Sky → Hobbs)
"""
import pytest
import json
import time
from pathlib import Path

# Test fixtures - clean up before/after tests
BASE = Path(__file__).resolve().parents[1]
BUS_FILE = BASE / "bus" / "messages.jsonl"
HOBBS_MEMORY_FILE = BASE / "src" / "agents" / "hobbs" / "memory" / "short_term.jsonl"
HOBBS_STATUS_FILE = BASE / "status" / "hobbs_last_msg.json"

@pytest.fixture
def clean_bus():
    """Clean bus file before and after test"""
    if BUS_FILE.exists():
        BUS_FILE.unlink()
    yield
    if BUS_FILE.exists():
        BUS_FILE.unlink()

@pytest.fixture
def clean_hobbs_memory():
    """Clean Hobbs memory before and after test"""
    if HOBBS_MEMORY_FILE.exists():
        HOBBS_MEMORY_FILE.unlink()
    yield
    if HOBBS_MEMORY_FILE.exists():
        HOBBS_MEMORY_FILE.unlink()

def test_publish_message(clean_bus):
    """Test publishing message to senate bus"""
    from src.senate_bus.broker import publish_json

    # Publish message
    result = publish_json("daily.data_ready", {
        "source": "sky",
        "task": "test_task",
        "status": "completed"
    })

    # Verify message was written
    assert BUS_FILE.exists()
    assert result["topic"] == "daily.data_ready"
    assert result["payload"]["source"] == "sky"

    # Read and verify format
    with BUS_FILE.open("r") as f:
        line = f.readline()
        msg = json.loads(line)
        assert "ts" in msg
        assert msg["topic"] == "daily.data_ready"
        assert msg["payload"]["task"] == "test_task"

def test_read_messages(clean_bus):
    """Test reading messages from bus"""
    from src.senate_bus.broker import publish_json, read_messages

    # Publish multiple messages
    publish_json("daily.data_ready", {"source": "sky", "task": "task1"})
    publish_json("task.completed", {"source": "hobbs", "task": "task2"})
    publish_json("daily.data_ready", {"source": "sky", "task": "task3"})

    # Read all messages
    all_messages = read_messages()
    assert len(all_messages) == 3

    # Read filtered by topic
    daily_messages = read_messages(topic_filter="daily.data_ready")
    assert len(daily_messages) == 2
    assert all(msg["topic"] == "daily.data_ready" for msg in daily_messages)

def test_consume_messages(clean_bus, clean_hobbs_memory):
    """Test Hobbs consuming messages from bus"""
    from src.senate_bus.broker import publish_json
    from src.agents.hobbs.inbox import consume_once

    # Publish message
    publish_json("daily.data_ready", {
        "source": "sky",
        "task": "garmin_pull",
        "status": "completed",
        "timestamp": time.time()
    })

    # Consume with Hobbs
    result = consume_once(topic="daily.data_ready")

    # Verify consumption result
    assert result["ok"] == True
    assert result["consumed"] >= 1
    assert "daily.data_ready" in result["topics"]

    # Verify message stored in Hobbs memory
    assert HOBBS_MEMORY_FILE.exists()
    with HOBBS_MEMORY_FILE.open("r") as f:
        memory_line = f.readline()
        memory_entry = json.loads(memory_line)
        assert memory_entry["type"] == "short"
        assert "senate" in memory_entry["tags"]
        assert "daily.data_ready" in memory_entry["tags"]
        assert memory_entry["source"] == "senate_bus"

    # Verify status file updated
    assert HOBBS_STATUS_FILE.exists()
    with HOBBS_STATUS_FILE.open("r") as f:
        status = json.load(f)
        assert status["action"] == "message_consumed"
        assert status["detail"]["topic"] == "daily.data_ready"

def test_publish_consume_cycle(clean_bus, clean_hobbs_memory):
    """Test full publish → consume cycle"""
    from src.senate_bus.broker import publish_json, read_messages
    from src.agents.hobbs.inbox import consume_messages

    # Sky publishes after garmin_pull
    publish_json("daily.data_ready", {
        "source": "sky",
        "task": "garmin_pull",
        "status": "completed",
        "data": {"sleep_hours": 7.5}
    })

    # Verify message in bus
    messages = read_messages(topic_filter="daily.data_ready")
    assert len(messages) == 1
    assert messages[0]["payload"]["data"]["sleep_hours"] == 7.5

    # Hobbs consumes
    result = consume_messages(topics=["daily.data_ready"])
    assert result["ok"] == True
    assert result["consumed"] == 1

    # Verify stored in Hobbs memory
    with HOBBS_MEMORY_FILE.open("r") as f:
        memory_entry = json.loads(f.readline())
        # Check that original message is preserved
        assert "original_message" in memory_entry
        assert memory_entry["original_message"]["payload"]["data"]["sleep_hours"] == 7.5

def test_multiple_topics(clean_bus, clean_hobbs_memory):
    """Test consuming from multiple topics"""
    from src.senate_bus.broker import publish_json
    from src.agents.hobbs.inbox import consume_messages

    # Publish to different topics
    publish_json("daily.data_ready", {"source": "sky", "task": "garmin"})
    publish_json("task.completed", {"source": "sky", "task": "report"})
    publish_json("memory.promoted", {"source": "sky", "entries": 5})

    # Consume from two topics
    result = consume_messages(topics=["daily.data_ready", "task.completed"])

    assert result["ok"] == True
    assert result["consumed"] == 2  # Only these two topics

def test_no_messages(clean_bus, clean_hobbs_memory):
    """Test consuming when no messages exist"""
    from src.agents.hobbs.inbox import consume_once

    # Try to consume from empty bus
    result = consume_once(topic="daily.data_ready")

    assert result["ok"] == True
    assert result["consumed"] == 0

def test_orchestrator_publishes_after_success():
    """Test that orchestrator publishes after successful garmin_pull"""
    from src.sky.orchestrator import SkyOrchestrator

    # This test verifies the orchestrator code structure
    # Actual execution would require real tool to exist
    orch = SkyOrchestrator()

    # Verify _publish_to_senate method exists
    assert hasattr(orch, '_publish_to_senate')
    assert callable(orch._publish_to_senate)

def test_message_format_validation(clean_bus):
    """Test message format adheres to spec"""
    from src.senate_bus.broker import publish_json, read_messages

    before_ts = time.time()
    publish_json("test.topic", {"key": "value"})
    after_ts = time.time()

    messages = read_messages()
    assert len(messages) == 1

    msg = messages[0]
    # Verify required fields
    assert "ts" in msg
    assert "topic" in msg
    assert "payload" in msg

    # Verify timestamp is reasonable
    assert before_ts <= msg["ts"] <= after_ts

    # Verify topic
    assert msg["topic"] == "test.topic"

    # Verify payload
    assert msg["payload"]["key"] == "value"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
