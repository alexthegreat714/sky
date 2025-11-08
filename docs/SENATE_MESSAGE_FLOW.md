# Senate Message Flow - Inter-Agent Communication

## Overview

The **Senate Bus** enables asynchronous message passing between agents in the Sky ecosystem. Agents can publish events and subscribe to topics without direct coupling.

**Current Phase (3):** Filesystem-backed queue (`bus/messages.jsonl`)
**Future Phase (4+):** Redis/RabbitMQ for production scale

---

## Architecture

```
┌──────────┐                    ┌──────────────┐                    ┌──────────┐
│   Sky    │                    │  Senate Bus  │                    │  Hobbs   │
│  Agent   │                    │              │                    │  Agent   │
└──────────┘                    └──────────────┘                    └──────────┘
     │                                 │                                   │
     │ 1. Task completes               │                                   │
     │    (garmin_pull)                │                                   │
     │                                 │                                   │
     │ 2. publish_json()               │                                   │
     ├────────────────────────────────>│                                   │
     │    topic: "daily.data_ready"    │                                   │
     │    payload: {source, task, ...} │                                   │
     │                                 │                                   │
     │                                 │ 3. Appends to                     │
     │                                 │    bus/messages.jsonl             │
     │                                 │                                   │
     │                                 │ 4. consume_messages()             │
     │                                 │<──────────────────────────────────│
     │                                 │    topic: "daily.data_ready"      │
     │                                 │                                   │
     │                                 │ 5. Returns matching messages      │
     │                                 ├──────────────────────────────────>│
     │                                 │                                   │
     │                                 │                      6. Stores in │
     │                                 │        hobbs/memory/short_term.jsonl
     │                                 │                                   │
     │                                 │                      7. Logs to   │
     │                                 │        status/hobbs_last_msg.json │
```

---

## Message Format

All messages in `bus/messages.jsonl` follow this schema:

```json
{
  "ts": 1699999999.123,
  "topic": "daily.data_ready",
  "payload": {
    "source": "sky",
    "task": "garmin_pull",
    "status": "completed",
    "timestamp": 1699999999.0
  }
}
```

**Fields:**
- `ts`: Unix timestamp when message was published
- `topic`: Message topic (dot-separated namespace)
- `payload`: Arbitrary JSON payload (agent-defined)

---

## Topic Namespace

Topics follow a hierarchical dot notation:

| Topic                  | Publisher | Subscribers | Purpose                           |
|------------------------|-----------|-------------|-----------------------------------|
| `daily.data_ready`     | Sky       | Hobbs       | Signals daily data pull complete  |
| `task.completed`       | Any       | Any         | Generic task completion           |
| `senate.vote_request`  | Any       | Aegis       | Request multi-agent vote          |
| `governance.alert`     | Any       | Aegis       | Constitutional violation alert    |
| `memory.promoted`      | Sky       | Hobbs       | Memory promoted to RAG            |

**Convention:**
- `{category}.{event_type}`
- Lowercase with underscores
- Use specific topics over generic ones

---

## Publishing Messages (Sky → Bus)

### From Orchestrator

**File:** `src/sky/orchestrator.py`

```python
# After successful task completion
if result.get("ok"):
    self._publish_to_senate("daily.data_ready", {
        "source": "sky",
        "task": "garmin_pull",
        "status": "completed",
        "timestamp": time.time()
    })
```

### Direct API

```python
from src.senate_bus.broker import publish_json

publish_json("daily.data_ready", {
    "source": "sky",
    "task": "custom_task",
    "data": {"key": "value"}
})
```

---

## Consuming Messages (Bus → Hobbs)

### From Hobbs Inbox

**File:** `src/agents/hobbs/inbox.py`

```python
from src.agents.hobbs.inbox import consume_messages

# Consume from specific topics
result = consume_messages(topics=["daily.data_ready", "task.completed"])

print(f"Consumed {result['consumed']} messages")
```

### What Happens

1. **Read messages** from `bus/messages.jsonl`
2. **Filter by topic** (e.g., "daily.data_ready")
3. **Store in Hobbs memory** (`hobbs/memory/short_term.jsonl`)
4. **Log status** to `status/hobbs_last_msg.json`

**Memory format:**
```json
{
  "ts": 1699999999.456,
  "type": "short",
  "content": "Senate message: {source: sky, task: garmin_pull, ...}",
  "tags": ["senate", "daily.data_ready"],
  "importance": 0.6,
  "source": "senate_bus",
  "original_message": {
    "ts": 1699999999.123,
    "topic": "daily.data_ready",
    "payload": {...}
  }
}
```

---

## Example Flow: Sky → Hobbs

### 1. Sky Completes Garmin Pull (06:45)

**Orchestrator executes:**
```python
# Run garmin_pull task
result = self._run_named_tool_chain(
    chain_name="garmin_pull",
    steps=[("run_approved_tools", "morning_garmin_downloader", ["--yesterday"])]
)

# Publish success to bus
if result.get("ok"):
    self._publish_to_senate("daily.data_ready", {
        "source": "sky",
        "task": "garmin_pull",
        "status": "completed",
        "timestamp": time.time()
    })
```

**Result:** `bus/messages.jsonl` appended:
```jsonl
{"ts": 1699999999.123, "topic": "daily.data_ready", "payload": {"source": "sky", "task": "garmin_pull", "status": "completed", "timestamp": 1699999999.0}}
```

### 2. Hobbs Consumes Message (Scheduled/Manual)

**Hobbs runs:**
```python
from src.agents.hobbs.inbox import consume_once

result = consume_once(topic="daily.data_ready")
```

**Result:** `hobbs/memory/short_term.jsonl` appended:
```jsonl
{"ts": 1700000000.0, "type": "short", "content": "Senate message: {source: sky, task: garmin_pull, ...}", "tags": ["senate", "daily.data_ready"], "importance": 0.6, "source": "senate_bus", "original_message": {...}}
```

**Status:** `status/hobbs_last_msg.json` updated:
```json
{
  "ts": 1700000000.0,
  "action": "message_consumed",
  "detail": {
    "topic": "daily.data_ready",
    "payload": {"source": "sky", "task": "garmin_pull", "status": "completed"},
    "consumed_count": 1
  }
}
```

### 3. Hobbs Acts on Data

Hobbs can now:
- Generate analysis report from Garmin data
- Trigger follow-up tasks
- Store insights to long-term memory
- Request additional context from Sky

---

## Message Lifecycle

### 1. Publication

```python
from src.senate_bus.broker import publish_json

publish_json("daily.data_ready", {"source": "sky", "task": "garmin_pull"})
```

**Creates:**
- Entry in `bus/messages.jsonl`
- Timestamped with `ts`
- Persistent until bus rotation (Phase 4+)

### 2. Consumption

```python
from src.senate_bus.broker import read_messages

messages = read_messages(topic_filter="daily.data_ready")
```

**Returns:**
- All messages matching topic
- In chronological order (by `ts`)
- Read-only (does not delete)

### 3. Storage

Consumers store messages in their own memory:
- Sky: `memory/short_term.jsonl`
- Hobbs: `hobbs/memory/short_term.jsonl`
- Aegis: `aegis/memory/short_term.jsonl`

### 4. Cleanup (Phase 4+)

Future cleanup strategies:
- **TTL-based**: Delete messages after 7 days
- **Consumption tracking**: Delete after all subscribers consume
- **Archive**: Move to `bus/messages_archive_{date}.jsonl`

---

## Testing Message Flow

**File:** `tests/test_senate_flow.py`

```python
from src.senate_bus.broker import publish_json, read_messages
from src.agents.hobbs.inbox import consume_once

# 1. Publish message
publish_json("daily.data_ready", {"source": "sky", "task": "test"})

# 2. Verify message in bus
messages = read_messages(topic_filter="daily.data_ready")
assert len(messages) > 0
assert messages[-1]["payload"]["task"] == "test"

# 3. Consume with Hobbs
result = consume_once(topic="daily.data_ready")
assert result["ok"] == True
assert result["consumed"] > 0
```

Run tests:
```bash
pytest tests/test_senate_flow.py -v
```

---

## Bus File Structure

**File:** `bus/messages.jsonl`

```jsonl
{"ts": 1699999990.0, "topic": "task.completed", "payload": {"task": "heartbeat"}}
{"ts": 1699999995.0, "topic": "daily.data_ready", "payload": {"source": "sky", "task": "garmin_pull"}}
{"ts": 1700000000.0, "topic": "memory.promoted", "payload": {"entries": 12, "threshold": 0.7}}
{"ts": 1700000005.0, "topic": "senate.vote_request", "payload": {"action": "restart_services", "requester": "sky"}}
```

**Properties:**
- Append-only (no edits)
- One message per line
- Chronological order
- No deletions (Phase 3)

---

## Multi-Agent Scenarios

### Scenario 1: Data Pipeline

```
Sky (garmin_pull) → Bus → Hobbs (analysis) → Bus → Sky (report)
```

1. Sky pulls Garmin data, publishes `daily.data_ready`
2. Hobbs consumes, analyzes, publishes `analysis.complete`
3. Sky consumes, generates report, publishes `report.ready`

### Scenario 2: Vote Request

```
Sky (needs authority) → Bus → Aegis (vote) → Bus → Sky (approved)
```

1. Sky needs restricted action, publishes `senate.vote_request`
2. Aegis consumes, evaluates, publishes `senate.vote_result`
3. Sky consumes, proceeds if approved

### Scenario 3: Memory Sync

```
Sky (promotes memory) → Bus → Hobbs (updates context)
```

1. Sky promotes memory to RAG, publishes `memory.promoted`
2. Hobbs consumes, updates shared knowledge context

---

## Phase 4+ Enhancements

### Redis Backend

```python
import redis

r = redis.Redis(host='localhost', port=6379)

def publish_json(topic: str, payload: Dict):
    r.publish(topic, json.dumps(payload))

def subscribe(topic: str, callback):
    pubsub = r.pubsub()
    pubsub.subscribe(topic)
    for message in pubsub.listen():
        callback(json.loads(message['data']))
```

**Benefits:**
- Real-time pub/sub
- TTL support
- Multi-server support
- Atomic operations

### Message Acknowledgment

```python
def consume_with_ack(topic: str):
    messages = read_messages(topic)
    for msg in messages:
        process(msg)
        ack_message(msg['id'])  # Mark as consumed
```

### Dead Letter Queue

Failed message processing → `bus/dead_letter.jsonl`

### Message Replay

```python
replay_messages(start_ts=1699999990, end_ts=1700000000)
```

---

## Troubleshooting

### Message Not Appearing

**Check:**
1. Publishing agent: Verify `publish_json()` called
2. Bus file: `cat bus/messages.jsonl | tail -10`
3. Topic spelling: Exact match required

### Hobbs Not Consuming

**Check:**
1. Inbox path: `src/agents/hobbs/inbox.py` exists
2. Import errors: `python -c "from src.agents.hobbs.inbox import consume_once"`
3. Status file: `cat status/hobbs_last_msg.json`

### Bus File Growing Large

**Solution:**
- Phase 3: Manual rotation (move to archive)
- Phase 4+: Automatic TTL cleanup

---

## Summary

The Senate Bus provides:
- ✅ Decoupled agent communication
- ✅ Persistent message log
- ✅ Topic-based routing
- ✅ Asynchronous processing
- ✅ Status tracking

**Current implementation:** Filesystem JSONL (simple, reliable)
**Future implementation:** Redis/RabbitMQ (scalable, real-time)
