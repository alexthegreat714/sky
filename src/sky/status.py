from pathlib import Path
import json, time
from .utils import ensure_dir

STATUS_DIR = Path("status")
ensure_dir(STATUS_DIR)

HEARTBEAT = STATUS_DIR / "sky_heartbeat.json"
LAST_ACTION = STATUS_DIR / "sky_last_action.json"

def write_heartbeat(extra=None):
    rec = {"ts": time.time(), "status": "ok"}
    if extra:
        rec.update(extra)
    HEARTBEAT.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")

def write_last_action(action: str, detail=None):
    rec = {"ts": time.time(), "action": action, "detail": detail or {}}
    LAST_ACTION.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")

def read_status():
    hb = json.loads(HEARTBEAT.read_text(encoding="utf-8")) if HEARTBEAT.exists() else {}
    la = json.loads(LAST_ACTION.read_text(encoding="utf-8")) if LAST_ACTION.exists() else {}
    return {"heartbeat": hb, "last_action": la}
