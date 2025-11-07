from fastapi import APIRouter
import os
import json
import datetime
from pathlib import Path


router = APIRouter()


def _daily_dir() -> Path:
    base = Path("open-webui-full/backend/data/sky_daily").resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base


@router.post("/api/sky/morning")
def receive_morning_digest(payload: dict):
    """Accept daily morning digest and store by date (UTC-local date).

    Stores to open-webui-full/backend/data/sky_daily/YYYY-MM-DD.json
    """
    date = datetime.date.today().isoformat()
    base = _daily_dir()
    path = base / f"{date}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return {"status": "ok", "stored": str(path)}


@router.get("/api/sky/today")
def get_today_summary():
    """Return today's stored digest JSON if present."""
    date = datetime.date.today().isoformat()
    path = _daily_dir() / f"{date}.json"
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "no report yet"}

