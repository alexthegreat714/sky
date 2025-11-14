import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

GARMIN_AGENTS_PATH = Path(r"C:\Users\blyth\Desktop\Engineering\Sky\agents")
GARMIN_DATA_PATH = Path(r"C:\Users\blyth\Desktop\Engineering\Sky\data\garmin_downloads")
GARMIN_DOWNLOAD_CACHE = Path(r"C:\Users\blyth\Desktop\Engineering\Sky\downloads\garmin")
DEFAULT_AGENT = "garmin_sleep_downloader.py"


def _safe_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _resolve_agent_script() -> Path:
    override = os.environ.get("SKY_GARMIN_AGENT_SCRIPT")
    candidate = GARMIN_AGENTS_PATH / (override or DEFAULT_AGENT)
    if not candidate.exists():
        raise FileNotFoundError(f"Garmin agent script missing: {candidate}")
    return candidate


def _move_downloads() -> List[str]:
    GARMIN_DATA_PATH.mkdir(parents=True, exist_ok=True)
    if not GARMIN_DOWNLOAD_CACHE.exists():
        return []

    moved: List[str] = []
    for csv_path in sorted(GARMIN_DOWNLOAD_CACHE.glob("*.csv")):
        dest = GARMIN_DATA_PATH / csv_path.name
        if dest.exists():
            dest = GARMIN_DATA_PATH / f"{csv_path.stem}_{_safe_timestamp()}{csv_path.suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(csv_path, dest)
        moved.append(dest.name)
    return moved


def list_downloaded_files() -> List[str]:
    if not GARMIN_DATA_PATH.exists():
        return []
    return sorted(p.name for p in GARMIN_DATA_PATH.glob("*.csv"))


def run_garmin_download() -> Dict[str, object]:
    """Invoke the legacy Garmin agent and return the current CSV inventory."""
    GARMIN_DATA_PATH.mkdir(parents=True, exist_ok=True)
    try:
        agent_path = _resolve_agent_script()
    except FileNotFoundError as exc:
        return {"status": "error", "error": str(exc), "staged_files": [], "files": []}

    summary: Dict[str, object] = {
        "status": "ok",
        "agent": str(agent_path),
        "staged_files": [],
        "files": [],
    }
    skip_agent = os.environ.get("SKY_SKIP_GARMIN_AGENT", "0") == "1"
    if not skip_agent:
        try:
            subprocess.run(
                [sys.executable, str(agent_path)],
                cwd=str(GARMIN_AGENTS_PATH),
                check=True,
            )
        except Exception as exc:
            summary["status"] = "error"
            summary["error"] = str(exc)

    moved = _move_downloads()
    summary["staged_files"] = moved
    summary["files"] = list_downloaded_files()
    return summary
