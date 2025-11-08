# Sky Orchestrator v1 (Scaffold)

## What it does
- Loads config and schedule (src/sky/schedule.yaml)
- Runs time-based tasks via SimpleScheduler (minute-level)
- Enforces constitutional authority before tool execution
- Writes heartbeat + last_action to /status/
- Exposes minimal API:
  - GET /health
  - GET /status

## Default tasks
- heartbeat: every 1 minute
- memory_rotate_check: every 10 minutes (noop in v1)
- garmin_pull: 06:45 daily → runs "morning_garmin_downloader --yesterday"
- morning_report: 07:10 daily → "morning_reporter --today" then "tts_morning_cli ..."

## How to run (later, when on your PC)
Loop-only (no API):
    python -m src.tools.run_sky --mode loop --seconds 60

Service mode (API on :7010):
    python -m src.tools.run_sky --mode service --port 7010

## Where to edit schedule
- src/sky/schedule.yaml

## Where status goes
- status/sky_heartbeat.json
- status/sky_last_action.json

## Authority enforcement
- Before any tool step, orchestrator checks governance.authority_gate.check_authority(action)
- If blocked: writes last_action with "authority_block"

## Next upgrades (v2)
- Event-driven hooks (bus + n8n webhooks)
- Retry/fallback chains
- Memory promotion pipeline
- RAG recall in planning loop
- Structured tool registry introspection
