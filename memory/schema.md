# Sky Memory Schema

## Overview

Sky's memory system consists of two tiers:
1. **Short-term memory** - Rotating context window (last 100 entries)
2. **Long-term memory** - Persistent, scored entries that survive pruning

## Memory Entry Format

All memory entries are stored in JSONL (JSON Lines) format.

### Short-Term Memory Entry

```json
{
  "timestamp": "2025-11-08T12:34:56.789Z",
  "content": "Generated morning report for 2025-11-08",
  "metadata": {
    "type": "action",
    "tool": "morning_reporter",
    "status": "success"
  },
  "score": 0
}
```

### Long-Term Memory Entry

```json
{
  "timestamp": "2025-11-08T12:34:56.789Z",
  "content": "User reported improved sleep quality after new bedtime routine",
  "score": 8,
  "metadata": {
    "type": "insight",
    "category": "health",
    "tags": ["sleep", "routine", "improvement"]
  },
  "committed": true
}
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO8601 string | Yes | UTC timestamp of memory creation |
| `content` | string | Yes | The actual memory content |
| `score` | integer (0-10) | Yes | Importance score for long-term promotion |
| `metadata` | object | No | Additional context (type, tags, etc.) |
| `committed` | boolean | Long-term only | Marks entry as committed to long-term |

## Scoring Guidelines

Memory entries are scored on importance:

| Score | Criteria | Example |
|-------|----------|---------|
| 0-2 | Routine action, low value | "Read short-term memory" |
| 3-4 | Normal action, some context | "Generated morning report" |
| 5-6 | Notable event or decision | "User changed morning routine" |
| 7-8 | Important insight or pattern | "Sleep quality improved by 15% over 7 days" |
| 9-10 | Critical system event | "Tool failure detected, escalated to Aegis" |

## Memory Lifecycle

1. **Creation**: All memories start in short-term storage
2. **Scoring**: Entries are scored based on importance
3. **Rotation**: When short-term exceeds 100 entries, oldest are pruned
4. **Promotion**: Entries with score ≥7 are promoted to long-term before pruning
5. **RAG Ingestion**: Long-term memories are embedded into RAG index
6. **Retrieval**: Sky can query both short-term and long-term memory

## Metadata Types

### Common metadata fields:

- `type`: `action`, `insight`, `error`, `escalation`, `user_interaction`
- `category`: `health`, `system`, `daily_briefing`, `tools`
- `tags`: Array of relevant keywords
- `tool`: Name of tool involved (if applicable)
- `status`: `success`, `failure`, `pending`
- `escalated_to`: Agent name if escalation occurred

## Privacy and Isolation

- Sky can ONLY read/write to `memory/sky/`
- Other agents (Hobbs, Apollo, etc.) have separate memory directories
- Cross-agent memory access is forbidden and logged as violation
- All memory operations are logged for audit trail

## Example Memory Workflows

### Workflow 1: Morning Report Generation

```jsonl
{"timestamp": "2025-11-08T07:00:00Z", "content": "Morning report workflow initiated", "score": 2, "metadata": {"type": "action", "workflow": "morning_briefing"}}
{"timestamp": "2025-11-08T07:00:05Z", "content": "Garmin sleep data retrieved: 7h 23m", "score": 4, "metadata": {"type": "data", "source": "garmin"}}
{"timestamp": "2025-11-08T07:00:10Z", "content": "Morning report generated successfully", "score": 3, "metadata": {"type": "action", "tool": "morning_reporter"}}
{"timestamp": "2025-11-08T07:00:15Z", "content": "TTS audio rendered", "score": 2, "metadata": {"type": "action", "tool": "tts_morning_cli"}}
```

### Workflow 2: Tool Failure Escalation

```jsonl
{"timestamp": "2025-11-08T07:00:00Z", "content": "Garmin downloader failed: connection timeout", "score": 6, "metadata": {"type": "error", "tool": "garmin_sleep_downloader"}}
{"timestamp": "2025-11-08T07:00:05Z", "content": "Retry attempt 1 failed", "score": 7, "metadata": {"type": "error", "retry": 1}}
{"timestamp": "2025-11-08T07:00:10Z", "content": "Escalated Garmin failure to Aegis", "score": 9, "metadata": {"type": "escalation", "escalated_to": "Aegis"}}
```

## Implementation Notes

- Files: `short_term.jsonl`, `long_term.jsonl`
- Max short-term entries: 100
- Promotion threshold: score ≥ 7
- Rotation: FIFO (first in, first out)
- Long-term: append-only (no deletion except manual pruning)
