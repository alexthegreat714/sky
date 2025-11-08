from pathlib import Path
import json, time

BASE = Path(__file__).resolve().parents[1]
LOG = BASE / "logs" / "sky_actions.jsonl"
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(action: str, detail: dict):
    rec = {
        "ts": time.time(),
        "action": action,
        **detail
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
