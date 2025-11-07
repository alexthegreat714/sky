Sky Morning Digest — rev-2025-11-02

Summary
- Adds a daily “Morning Digest” for Sky:
  - Backend route to store and fetch daily digest JSON.
  - Reporter script that parses Garmin sleep CSV, fetches real news, builds plans/food/advice, and posts the digest.
- Produces a readable, longer “sleep feedback” section (not just stats) with actionable guidance and a distinct word of advice.

Components
- Reporter: `Sky/agents/morning_reporter.py`
  - Reads latest Garmin CSV from `C:\Users\blyth\Desktop\Engineering\Sky\downloads\garmin` (pattern `sleep-*.csv`).
  - Generates: sleep_review, overnight_news, previous_day_news, plans_placeholder, food_recommendations, good_word_of_advice.
  - Saves JSON to `open-webui-full/backend/data/sky_daily/YYYY-MM-DD.json` and attempts a POST to OWUI.
- OWUI Router: `open-webui-full/backend/open_webui/routers/sky_morning.py`
  - `POST /api/sky/morning` → stores today’s digest to `open-webui-full/backend/data/sky_daily/YYYY-MM-DD.json`.
  - `GET /api/sky/today` → returns today’s JSON if present.

Usage
- Manual run now:
  - `python Sky\agents\morning_reporter.py`
  - Check file: `open-webui-full\backend\data\sky_daily\<today>.json`
- API (after OWUI backend restart):
  - POST: `http://127.0.0.1:3000/api/sky/morning`
  - GET:  `http://127.0.0.1:3000/api/sky/today`

Notes
- If POST returns 405, restart Open WebUI so the new router is loaded.
- News sources: BBC, Reuters, NPR (RSS/Atom) with longer summaries and deduped items (yesterday vs last 12h).
- Sleep feedback is two paragraphs: overall read + tailored suggestions for tonight.

Schedule (suggested)
- Garmin downloader: 06:55 local (CSV present).
- Morning digest: 07:05 local → `python C:\Users\blyth\Desktop\Engineering\Sky\agents\morning_reporter.py`

Next Steps
- Add an OWUI tool to display today’s digest in chat.
- Optionally append a brief headline to `open-webui-full/backend/data/sky_memory.txt`.
- Optional TTS integration after written flow stabilizes.

