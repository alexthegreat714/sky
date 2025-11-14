# Sky Agents Overview

## Current Garmin Morning Pipeline
These scripts power the live Garmin ingestion + digest workflow:

- `morning_reporter.py` – parses the newest staged Garmin CSV, generates the JSON/text digest, and posts to OWUI.
- `sky_morning_orchestrator.py` – orchestrates click replay → CSV staging → reporter (sets `SKY_GARMIN_TARGET_DATE` for accuracy).

Automation helpers (`garmin_click_replay.ps1`, `garmin_full_morning.bat`, etc.) live in `Sky/tools/`.

### Report Output
Successful runs save the digest to:
```
C:\Users\blyth\Desktop\Engineering\Sky\tools\open-webui-full\backend\data\sky_daily\<YYYY-MM-DD>.json
```

## Legacy Atlas Agents (Archived)
Retired Atlas-style agents have been moved to `Sky/agents/old/` for reference:

- `old/daily_info_agent.py`
- `old/sky_browser_agent.py`
- `old/garmin_sleep_downloader.py`
- `old/tts_morning_cli.py`

Refer to the files inside `old/` if you need the previous Atlas workflow or browser automation examples.
