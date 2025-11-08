# Sky Tool Registry

## Overview

Sky auto-discovers tools from multiple locations:
- `tools/` (legacy location)
- `src/agents/sky_tools/` (new structured location)
- `agents/` (Phase 1 legacy)

Tools are discovered automatically - no manual registration required!

## How to Create a Tool

### Basic Tool (Python script)

Create a Python script in any tool directory:

**File:** `tools/my_custom_tool.py`
```python
#!/usr/bin/env python3
"""
My Custom Tool - does something useful
"""
import sys

def main():
    print("Tool executed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

That's it! Sky will automatically discover it.

### Tool with Metadata (Optional)

Create a matching `.json` file for richer metadata:

**File:** `tools/my_custom_tool.json`
```json
{
  "description": "My custom tool does X, Y, and Z",
  "args": [
    {
      "name": "--input",
      "description": "Input file path",
      "required": true
    },
    {
      "name": "--output",
      "description": "Output file path",
      "required": false
    }
  ],
  "author": "Alex",
  "version": "1.0"
}
```

## Tool Discovery

When Sky starts, it scans all tool directories and builds a registry:

```python
from src.sky.tool_registry import list_tools

tools = list_tools()
# Returns: [
#   {
#     "name": "my_custom_tool",
#     "path": "/path/to/tools/my_custom_tool.py",
#     "description": "My custom tool does X, Y, and Z",
#     "args": [...],
#     "metadata": {...}
#   },
#   ...
# ]
```

## Tool Execution

### Programmatic Execution

```python
from src.sky.tool_registry import run_tool

result = run_tool("my_custom_tool", args=["--input", "data.csv"])

if result["ok"]:
    print("Success:", result["stdout"])
else:
    print("Failed:", result["stderr"])
```

### Via Orchestrator

Tools can be called from scheduled tasks:

**File:** `src/sky/schedule.yaml`
```yaml
daily:
  - name: "custom_task"
    time: "08:00"
```

**File:** `src/sky/orchestrator.py` (add handler)
```python
if name == "custom_task":
    return self._run_named_tool_chain(
        chain_name="custom_task",
        steps=[("run_approved_tools", "my_custom_tool", ["--input", "data.csv"])]
    )
```

### Via Webhook API

```bash
curl -X POST http://localhost:7010/run_tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "my_custom_tool",
    "args": ["--input", "data.csv"]
  }'
```

## Tool Return Format

All tools must exit with appropriate return codes:
- `0` = success
- Non-zero = failure

Output is captured via stdout/stderr:

```python
{
  "ok": true,              # True if rc == 0
  "stdout": "...",         # Standard output
  "stderr": "...",         # Standard error
  "rc": 0,                 # Return code
  "tool": "tool_name",     # Tool that was executed
  "cmd": "python ..."      # Full command executed
}
```

## How Sky Answers "What Tools Do You Have?"

When asked about available tools, Sky can query the registry:

```python
from src.sky.tool_registry import list_tools

def handle_tool_query():
    tools = list_tools()
    return {
        "total": len(tools),
        "tools": [
            {
                "name": t["name"],
                "description": t["description"]
            }
            for t in tools
        ]
    }
```

Example response:
```json
{
  "total": 5,
  "tools": [
    {"name": "garmin_sleep_downloader", "description": "Downloads sleep data from Garmin Connect"},
    {"name": "morning_reporter", "description": "Generates daily morning briefing"},
    {"name": "tts_morning_cli", "description": "Text-to-speech for morning reports"},
    {"name": "sky_browser_agent", "description": "Browser automation"},
    {"name": "daily_info_agent", "description": "Aggregates daily info"}
  ]
}
```

## Tool Search Paths

Tools are discovered in this order (first match wins):

1. `tools/` - Legacy Phase 1 tools
2. `src/agents/sky_tools/` - New structured location
3. `agents/` - Alternative legacy location

## Tool Naming Rules

- Tool name = Python filename without `.py`
- Must not start with `__` (reserved)
- Must not start with `test_` (test files)
- Case-sensitive
- Hyphens and underscores allowed

## Examples

### Simple Tool

**File:** `tools/hello.py`
```python
#!/usr/bin/env python3
"""Simple greeting tool"""
import sys

def main():
    print("Hello from Sky!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**Usage:**
```python
run_tool("hello")
# Output: {"ok": True, "stdout": "Hello from Sky!\n", ...}
```

### Tool with Arguments

**File:** `tools/echo.py`
```python
#!/usr/bin/env python3
"""Echo tool - prints arguments"""
import sys

def main():
    args = sys.argv[1:]
    print(" ".join(args))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**Usage:**
```python
run_tool("echo", args=["Hello", "World"])
# Output: {"ok": True, "stdout": "Hello World\n", ...}
```

## Error Handling

### Tool Not Found

```python
result = run_tool("nonexistent_tool")
# Returns:
# {
#   "ok": False,
#   "error": "Tool 'nonexistent_tool' not found",
#   "available_tools": ["tool1", "tool2", ...]
# }
```

### Tool Execution Failure

```python
result = run_tool("failing_tool")
# Returns:
# {
#   "ok": False,
#   "stdout": "...",
#   "stderr": "Error: something went wrong",
#   "rc": 1,
#   "tool": "failing_tool"
# }
```

### Tool Timeout

Tools have a 5-minute execution timeout:

```python
result = run_tool("slow_tool")
# If timeout:
# {
#   "ok": False,
#   "error": "Tool 'slow_tool' timed out after 300s"
# }
```

## Status Logging

All tool executions are logged to `status/sky_last_action.json`:

```json
{
  "ts": 1699999999.123,
  "action": "tool_executed",
  "detail": {
    "name": "my_custom_tool",
    "rc": 0
  }
}
```

Failed executions log additional detail:
```json
{
  "ts": 1699999999.456,
  "action": "tool_failed",
  "detail": {
    "name": "failing_tool",
    "rc": 1
  }
}
```

## TODO Phase 4+

- [ ] Tool permission levels (some tools require sudo/elevation)
- [ ] Tool dependency checking (ensure required tools/packages installed)
- [ ] Tool versioning (handle breaking changes)
- [ ] Tool output parsing (structured JSON responses)
- [ ] Tool retry logic (automatic retry on transient failures)
- [ ] Tool caching (cache expensive tool results)
- [ ] Tool composition (chain tools together declaratively)
