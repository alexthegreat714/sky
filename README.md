# Sky RAG + Chat Reference

Sky runs on port **5011** and mirrors the Aegis prompt stack while remaining IO-isolated (no audio capture yet).

## Phase 7.5: Tool Awareness + Garmin Data

- **Tool registry** – `GET /tools` refreshes `Sky/tool_registry.py`, enumerates every module/function, and mirrors the snapshot to `C:\Users\blyth\Desktop\Engineering\rag_data\Sky\logs\tool_registry.json`.
- **Garmin pipeline** – drop CSVs under `C:\Users\blyth\Desktop\Engineering\Sky\data\garmin_downloads`, then `POST /garmin/run` parses anything new and emits JSON+TXT summaries in `...\Sky\reports\garmin_reports`. `GET /garmin/status` surfaces the drop folder plus newly detected files.
- **Nightly proof tasks** – `Sky/autorun_supervisor.py` captures the nightly pipeline run (summary + screenshot) in `C:\Users\blyth\Desktop\Engineering\rag_data\Sky\logs\autorun_evidence`. The global `bin\agent_supervisor.py` scheduler now triggers this alongside the existing Aegis autorun window.
- **Audio recorder TODO (not active)**  
  1. Add a gated `audio_recorder.py` module that acquires explicit CLI/env approval before touching microphones.  
  2. Extend `app.py` with a disabled `/audio/status` + `/audio/start` pair guarded by a hardware whitelist and runtime metrics hooks.  
  3. Store raw clips under `rag_data\Sky\audio` with checksum manifests + retention limits, then surface metadata to the tool registry.  
  4. Ship regression tests that prove no recording occurs unless the opt-in flag + policy document hash are present.  
  Until those four items are complete, Sky simply documents the workflow and keeps audio capture offline.

## Phase 7.6: Agent-Driven Garmin Pipeline

## Phase 7.6: Agent-Driven Garmin Pipeline (with human-safe export)

- Endpoints (Sky):
  - `POST /garmin/full_run` → orchestrates download → ingest → report via the bridge (for automated runs).
  - `GET /garmin/files` → lists staged CSVs.

- Bridge & pipeline:
  - `Sky/garmin_agents_bridge.py` wraps the legacy automation (`Sky\agents\garmin_sleep_downloader.py`) and can copy CSVs into `Sky\data\garmin_downloads` for pipeline stats.
- Test harness `tests\EchoRun_Sky_v7.6.bat` boots Sky, hits `/garmin/full_run`, `/garmin/files`, `/metrics`, and logs to `tests\logs\sky_v7.6_*.txt`.

- Morning automation summary:
  - Chat shortcuts: `/garmin help|status|files|run [today|yesterday|YYYY-MM-DD]`, `/morning show|path [date]`.
  - Sweep lockfile: `Sky\jobs\morning_<ISO>.lock` prevents duplicate runs for the same date.
  - Reporter CLI: `python agents\morning_reporter.py --date 2025-11-12` (falls back to newest CSV when omitted).
  - Inbox: `Sky\downloads\garmin\sleep-<ISO>_Sky_<timestamp>.csv`.
  - Digests: `open-webui-full\backend\data\sky_daily\<ISO>.json`.
  - Last-run marker: `Sky\logs\morning_orchestrator\last.json` (also served at `/ops/last`).
  - Selector check helper: `Sky\tools\check_selectors.ps1` verifies the Garmin menu/export selectors.

- Morning Digest (reporter):
  - `Sky\agents\morning_reporter.py` builds the daily JSON digest (sleep review + news + plans/food/advice) and writes to:
    `C:\Users\blyth\Desktop\Engineering\open-webui-full\backend\data\sky_daily\YYYY-MM-DD.json`
  - The reporter reads the newest CSV from `C:\Users\blyth\Desktop\Engineering\Sky\downloads\garmin` and honors `SKY_GARMIN_TARGET_DATE` if set.

- New all-in-one morning tool (human-safe export + staging + report):
  - **Path:** `C:\Users\blyth\Desktop\Engineering\Sky\tools\garmin_full_morning.bat`
  - **What it does (blocking, in one window):**
    1) Runs PowerShell click replay to open Garmin Sleep for the target date and click **Export CSV** (`garmin_click_replay.ps1`).
    2) Verifies the file in `%USERPROFILE%\Downloads` (supports `sleep-YYYY-MM-DD*.csv` and `Sleep.csv`).
    3) Copies it to `C:\Users\blyth\Desktop\Engineering\Sky\downloads\garmin` as `sleep-<ISO>_Sky_<timestamp>.csv` (original stays in Downloads).
    4) Sets `SKY_GARMIN_TARGET_DATE=<ISO>` and runs `Sky\agents\morning_reporter.py`.
    5) Prints the expected digest path and the reporter exit code.
  - **Args:** `TODAY`, `YESTERDAY` (default), or `YYYY-MM-DD`:
    ```
    C:\Users\blyth\Desktop\Engineering\Sky\tools\garmin_full_morning.bat
    C:\Users\blyth\Desktop\Engineering\Sky\tools\garmin_full_morning.bat TODAY
    C:\Users\blyth\Desktop\Engineering\Sky\tools\garmin_full_morning.bat 2025-11-12
    ```
  - **Internals used by the .bat:**
    - `C:\Users\blyth\Desktop\Engineering\Sky\tools\garmin_click_replay.ps1` (opens page, replays recorded clicks)
    - (staging is performed inline; no separate script required)

- Guardrails (unchanged):
  - No destructive wipe endpoints.
  - POST with JSON for filterable ops; GET only for health/meta/list/export.
  - Local providers only (Ollama / Open WebUI); no external network dependencies.
  - Audio/TTS (`run_morning_tts.bat`, `tts_morning_cli.py`) remain disabled until hardening is complete.

## Core Endpoints
- `POST /chat` – main conversation endpoint on port 5011 (Aegis-style prompt orbit, branded as Sky).
- `GET /tools` – returns the current module/function inventory plus the persisted registry file path.
- `POST /garmin/run` – executes the Garmin CSV ingestion + summary generator.
- `GET /garmin/status` – lists raw CSV files and highlights anything still waiting to be processed.
- `POST /rag/write`, `POST /rag/search`, `POST /rag/review` – identical semantics to Aegis, scoped to `rag_data\Sky`.
- `GET /rag/count` – total number of Sky memories.
- `POST /rag/count` – accepts `{"where": {...}, "min_priority": 0.8}` for filtered totals (exact-match only).
- `GET /rag/list` / `POST /rag/list` – GET for ID-only paging, POST for JSON-filtered `[{id,text,meta}]` payloads.
- `GET /rag/export` / `POST /rag/import` – JSONL backups live under `C:\Users\blyth\Desktop\Engineering\Sky\logs`.
- `POST /rag/delete`, `POST /rag/update`, `GET /rag/get`, `GET /rag/tags` – admin/ops helpers.

## Filters
- Only direct equality filters are supported (e.g., `{"source":"ops"}`); nested operators are rejected.
- Use the POST variants for any filtered counts or listings. GET routes stay unauthenticated and ignore query params.
- `min_priority` is optional; omit it to include all entries.

## Export / Import Examples

**cmd.exe**
```
curl http://127.0.0.1:5011/rag/export -o C:\Users\blyth\Desktop\Engineering\Sky\logs\rag_export.jsonl
curl -X POST http://127.0.0.1:5011/rag/import ^
  -H "Content-Type: application/json" ^
  -d "{\"path\":\"C:\\\\Users\\\\blyth\\\\Desktop\\\\Engineering\\\\Sky\\\\logs\\\\rag_export.jsonl\"}"
```

**PowerShell**
```powershell
$out = 'C:\Users\blyth\Desktop\Engineering\Sky\logs\rag_export.jsonl'
Invoke-WebRequest -Uri http://127.0.0.1:5011/rag/export -OutFile $out
Invoke-RestMethod -Uri http://127.0.0.1:5011/rag/import -Method Post `
  -Body (@{ path = $out } | ConvertTo-Json) -ContentType 'application/json'
```

## Encoding / BOM Note
Sky shares the same BOM-tolerant JSONL importer as Aegis. UTF-8/UTF-16 dumps, even with BOMs, are accepted; invalid or non-primitive metadata is skipped and reported via the `skipped` counter.

## Smoke Tests
```
python C:\Users\blyth\Desktop\Engineering\Sky\rag_smoke.py
curl -X POST http://127.0.0.1:5011/rag/count -H "Content-Type: application/json" -d "{\"where\":{\"source\":\"ops\"}}"
tests\EchoRun_Sky_v7.5.bat
python C:\Users\blyth\Desktop\Engineering\Sky\autorun_supervisor.py
```
