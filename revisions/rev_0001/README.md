# Sky Stack – Revision rev_0001 (2025-11-02 UTC)

This revision captures the initial end-to-end setup for a local “Atlas‑style” stack:

- Daily web info agent (Playwright) and a browser-use agent
- Garmin sleep downloader with persistent Chrome profile and click‑to‑capture
- Watchdog service for health checks and daily reporting
- Memory integration with Open WebUI (OWUI)

## Contents

- Agents
  - `Sky/agents/daily_info_agent.py` – Fetches sites, extracts text, summarizes via local LLM, appends to memory
  - `Sky/agents/sky_browser_agent.py` – Agentic browsing; summarizes and appends to memory
  - `Sky/agents/garmin_sleep_downloader.py` – Two-click download (3‑dots → Export CSV) with persistent Chrome profile
  - `Sky/agents/garmin_wizard.bat` – Interactive menu for login, checks, selector capture, and runs
  - `Sky/agents/garmin_setup.bat`, `Sky/agents/garmin_download_yesterday.bat` – Shortcuts
- Selectors snapshot (this rev)
  - `Sky/revisions/rev_0001/garmin_selectors.json`
- Watchdog
  - `Sky/watchdog/watchdog.py` – Health checks (LLM, HTTP, ping, restart/fallback attempts) + daily memory summary
  - Config snapshot (this rev): `Sky/revisions/rev_0001/watchdog_config.json`
  - Live config: `Sky/watchdog/config.json`
- Memory and status locations
  - Memory: `open-webui-full/backend/data/sky_memory.txt`
  - Watchdog status JSON: `open-webui-full/backend/data/sky_watchdog/status.json`

## What We Built

### Daily Info Agent
- Async Playwright. Visits a URL list, extracts visible text, summarizes via a local LLM, appends blocks to memory.
- Auto‑probes endpoints: OpenAI‑style `/v1/chat/completions`, Ollama `/api/chat` and `/api/generate`.
- CLI: `--test` (run once), `--run` (09:00 UTC loop).
- Log: `Sky/agents/daily_info_log.txt`.

### Browser Agent
- Uses `browser-use` with a stable `BrowserSession`. Performs tasked browsing, captures page text, summarizes, appends to memory.
- Auto‑probes summarization endpoint similar to daily agent.
- CLI: `--task`, `--headless/--no-headless`.
- Log: `Sky/agents/browser_agent_log.txt`.

### Garmin Downloader
- Persistent Chrome profile so you log in once and never share credentials.
- Deterministic two clicks: (1) kebab 3‑dots, (2) Export CSV.
- Click‑to‑capture mode: you click elements headfully; script records attributes and writes robust selectors to `garmin_selectors.json`.
- Wizard BAT provides guided options (login, check, capture, test, download yesterday).
- Downloads path: `C:\Users\blyth\Desktop\Engineering\Sky\downloads\garmin`.

### Watchdog
- Probes LLM endpoints, HTTP targets, and ping hosts; attempts restart/fallback for declared servers/tunnels.
- Writes a structured JSON status and one compact memory summary per UTC day.
- Outputs:
  - Status JSON: `open-webui-full/backend/data/sky_watchdog/status.json`
  - Memory line: `open-webui-full/backend/data/sky_memory.txt`
  - Log: `Sky/watchdog/watchdog_log.txt`

## How We Verified

- Daily Agent: ran `--test`; pivoted to a working local endpoint (Ollama) and appended to memory.
- Browser Agent: ran a sample query task; appended a summary to memory.
- Garmin: headful test succeeded; saved CSV as `sleep-YYYY-MM-DD-Sleep.csv`.
- Watchdog: inserted fake targets to exercise failures; confirmed JSON and daily memory entry.

## Usage Cheatsheet

- Daily info (once): `python Sky\agents\daily_info_agent.py --test`
- Browser task: `python Sky\agents\sky_browser_agent.py --task "query"`
- Garmin wizard: `Sky\agents\garmin_wizard.bat`
  - 1) One‑time login
  - 4) Select clicks (click 3‑dots then CSV) – saves selectors
  - 5) Test headful
  - 6) Download yesterday (headless)
- Watchdog (one pass): `python Sky\watchdog\watchdog.py`

## Next Steps

- Schedule Garmin: add a Windows Scheduled Task at your preferred time (after data finalizes).
- Expand Watchdog: add a check that verifies a new CSV exists daily; log “Garmin OK” with file size.
- Align OWUI memory paths if you want OWUI to ingest agent outputs automatically.
- Improve site extractors in daily agent and richer summarization templates.

## Changelog (rev_0001)

- Implemented agents (daily + browser‑use) with endpoint probing and memory appends.
- Built Garmin downloader with persistent login, selector capture, and wizard flows.
- Introduced watchdog with health probes, restart hooks, and daily summaries.
- Verified flows headfully and headlessly; captured selectors/config into this revision.

