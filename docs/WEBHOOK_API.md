# Sky Webhook API

External systems can trigger Sky actions via HTTP webhooks.

**Base URL:** `http://localhost:7010` (or your configured service port)

**Version:** 0.2

---

## Endpoints

### GET /health

Health check

**Response:**
```json
{
  "status": "ok",
  "component": "sky",
  "phase": "orchestrator-v1"
}
```

---

### GET /status

Get current status (heartbeat + last action)

**Response:**
```json
{
  "heartbeat": {
    "ts": 1699999999.123,
    "status": "ok",
    "orchestrator": "running"
  },
  "last_action": {
    "ts": 1699999999.456,
    "action": "tool_executed",
    "detail": {"name": "morning_reporter", "rc": 0}
  }
}
```

---

### GET /tools

List all discovered tools

**Response:**
```json
{
  "total": 5,
  "tools": [
    {
      "name": "morning_reporter",
      "description": "Generates daily morning briefing"
    },
    {
      "name": "garmin_sleep_downloader",
      "description": "Downloads sleep data from Garmin Connect"
    }
  ]
}
```

---

### POST /run_task

Execute a scheduled task by name

**Authority Required:** `run_approved_tools`

**Request:**
```json
{
  "task": "garmin_pull"
}
```

**Success Response (200):**
```json
{
  "ok": true,
  "results": [
    {
      "tool": "morning_garmin_downloader",
      "result": {
        "ok": true,
        "stdout": "Downloaded sleep data for 2025-11-08\n",
        "rc": 0
      }
    }
  ]
}
```

**Error Response (403 - Authority Blocked):**
```json
{
  "detail": "⚠️ Action blocked: \"run_approved_tools\" exceeds Sky's authority. Escalate to aegis or alex."
}
```

**Error Response (400 - Task Failed):**
```json
{
  "detail": "unknown task: invalid_task_name"
}
```

---

### POST /run_tool

Execute a specific tool with arguments

**Authority Required:** `run_approved_tools`

**Request:**
```json
{
  "tool": "morning_reporter",
  "args": ["--today"]
}
```

**Success Response (200):**
```json
{
  "ok": true,
  "stdout": "Report generated successfully\n",
  "stderr": "",
  "rc": 0,
  "tool": "morning_reporter",
  "cmd": "python /path/to/morning_reporter.py --today"
}
```

**Error Response (403 - Authority Blocked):**
```json
{
  "detail": "⚠️ Action blocked: \"run_approved_tools\" exceeds Sky's authority. Escalate to aegis or alex."
}
```

**Error Response (400 - Tool Not Found):**
```json
{
  "detail": "Tool 'nonexistent_tool' not found"
}
```

**Error Response (400 - Tool Failed):**
```json
{
  "detail": "Tool execution failed: subprocess error"
}
```

---

## Usage Examples

### cURL

**Run a task:**
```bash
curl -X POST http://localhost:7010/run_task \
  -H "Content-Type: application/json" \
  -d '{"task": "heartbeat"}'
```

**Run a tool:**
```bash
curl -X POST http://localhost:7010/run_tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "morning_reporter",
    "args": ["--today"]
  }'
```

**List tools:**
```bash
curl http://localhost:7010/tools
```

**Check status:**
```bash
curl http://localhost:7010/status
```

---

### Python (requests)

```python
import requests

# List available tools
response = requests.get("http://localhost:7010/tools")
tools = response.json()
print(f"Available tools: {tools['total']}")

# Run a task
response = requests.post(
    "http://localhost:7010/run_task",
    json={"task": "garmin_pull"}
)
if response.status_code == 200:
    result = response.json()
    print(f"Task succeeded: {result['ok']}")
else:
    print(f"Task failed: {response.status_code} - {response.json()}")

# Run a tool with arguments
response = requests.post(
    "http://localhost:7010/run_tool",
    json={
        "tool": "morning_reporter",
        "args": ["--date", "2025-11-08"]
    }
)
if response.status_code == 200:
    result = response.json()
    print(f"Output: {result['stdout']}")
else:
    print(f"Error: {response.json()['detail']}")
```

---

### n8n Workflow

**HTTP Request Node:**

```json
{
  "method": "POST",
  "url": "http://localhost:7010/run_tool",
  "body": {
    "tool": "morning_reporter",
    "args": ["--today"]
  },
  "headers": {
    "Content-Type": "application/json"
  }
}
```

**Conditional Node (check success):**
```javascript
// Check if tool succeeded
return items.map(item => ({
  json: {
    success: item.json.ok === true
  }
}));
```

---

## Error Handling

### Authority Blocked (403)

When Sky's constitutional authority gate blocks an action:

```bash
curl -X POST http://localhost:7010/run_tool \
  -H "Content-Type: application/json" \
  -d '{"tool": "restart_server"}'

# Response (403):
{
  "detail": "⚠️ Action blocked: \"run_approved_tools\" exceeds Sky's authority. Escalate to aegis or alex."
}
```

**Action:** Request authorization from Aegis or Alex

**Status file updated:**
```json
{
  "ts": 1699999999.789,
  "action": "webhook_tool_blocked",
  "detail": {
    "tool": "restart_server",
    "reason": "Authority gate blocked"
  }
}
```

---

### Tool Not Found (400)

```bash
curl -X POST http://localhost:7010/run_tool \
  -H "Content-Type: application/json" \
  -d '{"tool": "unknown_tool"}'

# Response (400):
{
  "detail": "Tool 'unknown_tool' not found"
}
```

**Action:** Check available tools via `GET /tools`

---

### Tool Execution Failed (400)

```bash
curl -X POST http://localhost:7010/run_tool \
  -H "Content-Type: application/json" \
  -d '{"tool": "failing_tool"}'

# Response (400):
{
  "detail": "Error: missing required argument --input"
}
```

**Action:** Check tool documentation and provide correct arguments

---

### Unknown Task (400)

```bash
curl -X POST http://localhost:7010/run_task \
  -H "Content-Type: application/json" \
  -d '{"task": "invalid_task"}'

# Response (400):
{
  "detail": "unknown task: invalid_task"
}
```

**Action:** Check `src/sky/schedule.yaml` for valid task names

---

## Status File Updates

All webhook requests update `status/sky_last_action.json`:

**Successful tool execution:**
```json
{
  "ts": 1699999999.123,
  "action": "webhook_tool_triggered",
  "detail": {
    "tool": "morning_reporter",
    "args": ["--today"]
  }
}
```

**Authority blocked:**
```json
{
  "ts": 1699999999.456,
  "action": "webhook_tool_blocked",
  "detail": {
    "tool": "restart_server",
    "reason": "Action blocked by authority gate"
  }
}
```

**Task triggered:**
```json
{
  "ts": 1699999999.789,
  "action": "webhook_task_triggered",
  "detail": {
    "task": "garmin_pull"
  }
}
```

---

## Security

### Authority Enforcement

All webhook endpoints enforce constitutional authority:

1. **Check:** `check_authority("run_approved_tools")`
2. **If blocked:** Return 403 + refusal message
3. **If allowed:** Execute + log to status

### Safe Defaults

If governance module not available:
- Conservative blocking: `restart_services`, `modify_system_configs`, `financial_transactions`, `self_upgrade`
- All other actions allowed

### TODO Phase 4+

- [ ] API key authentication
- [ ] Rate limiting
- [ ] Request signing (verify caller identity)
- [ ] Webhook secret validation
- [ ] IP whitelist
- [ ] OAuth integration
- [ ] Audit log (separate from status file)
