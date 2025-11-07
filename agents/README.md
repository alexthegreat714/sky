# Sky Agents (Atlas‑style) – Daily Info Agent and Browser Agent

This directory contains two local “Atlas‑style” agents that fetch/browse daily information, summarize it with your local LLM, and append results to Sky memory.

- Daily Info Agent: `Sky/agents/daily_info_agent.py`
- Browser Agent: `Sky/agents/sky_browser_agent.py`
- Memory target: `open-webui-full/backend/data/sky_memory/memory.txt`
- Logs: `Sky/agents/daily_info_log.txt`, `Sky/agents/browser_agent_log.txt`

Note: Your repo also has `open-webui-full/backend/data/sky_memory.txt`. The agents write to `.../sky_memory/memory.txt` (subfolder). This separation avoids clobbering the top-level file.


## What’s Included

- Daily Info Agent (Playwright)
  - Launches headless Chromium, visits a URL list, extracts titles/snippets, summarizes, and appends timestamped entries.
  - CLI flags: `--test` (run once), `--run` (daily loop at 09:00 UTC).
  - Logs to `Sky/agents/daily_info_log.txt`.

- Browser Agent (browser-use)
  - Uses `browser-use` session API (Chromium) to perform a search/task, captures page text state, summarizes, and appends entries.
  - CLI flags: `--task`, `--headless/--no-headless`, `--max-steps`.
  - Logs to `Sky/agents/browser_agent_log.txt`.

- Endpoint auto‑detection and adapters
  - Probes common local endpoints and selects a working one plus a usable model.
  - Supports three summarization styles:
    - OpenAI‑style: `…/v1/chat/completions`
    - Ollama chat: `…/api/chat`
    - Ollama generate: `…/api/generate`


## Requirements

- Python 3.11+
- Packages:
  - `pip install playwright requests browser-use`
  - `python -m playwright install chromium`
- Local LLM endpoint (one of):
  - OpenAI‑compatible server (e.g., Open WebUI backend) at `http://127.0.0.1:3000/v1/chat/completions` (or your port)
  - Ollama at `http://127.0.0.1:11434`

Optional environment variables:
- Tokens (if your backend requires them): `OPENAI_API_KEY`, `OPENWEBUI_API_KEY`
- Daily agent: `DAILY_AGENT_LLM_ENDPOINT`, `DAILY_AGENT_LLM_MODEL`
- Browser agent (summarization): `SKY_BROWSER_SUMMARIZE_ENDPOINT`, `SKY_BROWSER_SUMMARIZE_MODEL`


## How Endpoint Probing Works

On each run, agents try a list of endpoints and pick the first that returns a good response:

1) OpenAI‑style: `http://127.0.0.1:3000/v1/chat/completions`, `http://127.0.0.1:8080/v1/chat/completions`
2) Ollama chat: `http://127.0.0.1:11434/api/chat`
3) Ollama generate: `http://127.0.0.1:11434/api/generate`

- If Ollama is detected, the agents query `/api/tags` and auto‑select the first available model when `--model auto`.
- You can override endpoint and model via CLI flags.

Tip: If `:3000` responds with HTTP 405, it’s likely a UI path, not an OpenAI API. The agents will automatically fall back to Ollama if available.


## Running the Agents

Daily Info Agent (single run):

```
python Sky\agents\daily_info_agent.py --test
```

Override URLs and endpoint/model:

```
python Sky\agents\daily_info_agent.py --test \
  --urls https://news.ycombinator.com https://www.bbc.com/news \
  --endpoint http://127.0.0.1:11434/api/generate --model llama3
```

Browser Agent (tasked run):

```
python Sky\agents\sky_browser_agent.py --task "latest hypersonics material testing" --headless
```

Options:
- `--no-headless` to see the browser
- `--max-steps 5` for future agent expansion
- Override summarization endpoint/model:

```
python Sky\agents\sky_browser_agent.py --task "L3Harris hypersonic propulsion" \
  --endpoint http://127.0.0.1:11434/api/chat --model llama3
```


## Output Format

Entries are appended to `open-webui-full/backend/data/sky_memory/memory.txt` like:

```
[YYYY-MM-DD HH:MM] Summary from {URL}:
{summary}
---

[YYYY-MM-DD HH:MM] Browser Agent Summary: {summary}
---
```


## Scheduling (Windows Task Scheduler)

A daily task has been created to run the daily info agent at 09:00 UTC (converted to your local time):
- Task name: `SkyDailyInfoAgentUTC9`
- Command: `python C:\Users\blyth\Desktop\Engineering\Sky\agents\daily_info_agent.py --test`

Manage via PowerShell:

```
# See next run time
Get-ScheduledTask -TaskName 'SkyDailyInfoAgentUTC9' | Get-ScheduledTaskInfo

# Run now
Start-ScheduledTask -TaskName 'SkyDailyInfoAgentUTC9'

# Remove
Unregister-ScheduledTask -TaskName 'SkyDailyInfoAgentUTC9' -Confirm:$false
```

If you prefer a fixed local time, we can create another task with your desired schedule.


## Troubleshooting

- HTTP 405 on `:3000` for chat: That’s probably not an OpenAI‑compatible API path. Use your backend’s `/v1/chat/completions` route or switch to Ollama.
- Low‑quality summaries: Use a more general model in Ollama, e.g., `ollama pull llama3`, then pass `--model llama3`.
- Extraction issues (cookie banners/captchas): The daily agent tries to click common consent buttons; the browser agent can be extended with more actions.


## Next Steps (You)

- Pick your preferred summarizer:
  - For Ollama: `ollama pull llama3`, then run with `--model llama3`.
- Curate sources and tasks:
  - Update the daily agent URL list to your focus areas.
  - Provide concrete daily tasks for the browser agent (company/tech watchlists).
- Confirm scheduling time:
  - Adjust to your desired local time (I can set up a new scheduled task).
- Optional: Create a second scheduled task for the browser agent with a standard daily query.


## Next Steps (Me)

- Browser agent improvements:
  - Implement fuller “search → open top result(s) → extract” flows, banner handling, and simple anti‑bot mitigations.
- Daily agent extraction refinements:
  - Site‑specific selectors, de‑duplication, and better snippet trimming.
- Preflight health checks:
  - Add an explicit endpoint readiness check and fail‑fast with clear log messages.
- Memory/RAG enrichment:
  - Add metadata/category tagging, and coordinate with `open-webui-full/backend/modules/sky_memory.py` for long‑term memory growth.

If you want me to take any of these next steps now—model switch, site list curation, better extraction, or a scheduled task for the browser agent—say the word and I’ll implement it.

