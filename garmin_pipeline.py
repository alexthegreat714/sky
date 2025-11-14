import json
import math
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .garmin_agents_bridge import run_garmin_download

DATA_ROOT = Path(r"C:\Users\blyth\Desktop\Engineering\Sky")
GARMIN_DATA_PATH = DATA_ROOT / "data" / "garmin_downloads"
GARMIN_REPORT_PATH = DATA_ROOT / "reports" / "garmin_reports"
GARMIN_LOG_PATH = Path(r"C:\Users\blyth\Desktop\Engineering\rag_data\Sky\logs")
GARMIN_STATE_FILE = GARMIN_LOG_PATH / "garmin_pipeline_state.json"


def _ensure_dirs() -> None:
    GARMIN_DATA_PATH.mkdir(parents=True, exist_ok=True)
    GARMIN_REPORT_PATH.mkdir(parents=True, exist_ok=True)
    GARMIN_LOG_PATH.mkdir(parents=True, exist_ok=True)


def _load_state() -> Dict[str, dict]:
    _ensure_dirs()
    if GARMIN_STATE_FILE.exists():
        try:
            return json.loads(GARMIN_STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"processed": {}, "last_run": None}


def _save_state(state: Dict[str, dict]) -> None:
    GARMIN_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_new_files(state: Dict[str, dict] | None = None) -> List[str]:
    """List Garmin CSV files that are new or changed since the last run."""
    _ensure_dirs()
    state = state or _load_state()
    processed = state.get("processed", {})
    pending: List[str] = []
    for file_path in sorted(GARMIN_DATA_PATH.glob("*.csv")):
        digest = _hash_file(file_path)
        recorded = processed.get(file_path.name, {})
        if recorded.get("sha256") != digest:
            pending.append(file_path.name)
    return pending


def load_csv(path: Path) -> pd.DataFrame:
    """Load and normalize a Garmin CSV."""
    df = pd.read_csv(path)
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    return df


def _sanitize(value):
    if value is pd.NA:
        return None
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if hasattr(value, "item"):
        try:
            val = value.item()
            return _sanitize(val)
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return str(value)


def generate_report(df: pd.DataFrame, filename: str) -> Dict[str, object]:
    """Generate JSON + text report summarizing the Garmin data."""
    _ensure_dirs()
    timestamp = datetime.now().isoformat()
    stats = df.describe(include="all").fillna(value=pd.NA).to_dict()
    summary = {
        "file": filename,
        "timestamp": timestamp,
        "rows": len(df),
        "columns": list(df.columns),
        "stats": _sanitize(stats),
    }

    base = Path(filename).stem
    json_path = GARMIN_REPORT_PATH / f"{base}_summary.json"
    text_path = GARMIN_REPORT_PATH / f"{base}_summary.txt"

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        f"Garmin Report :: {filename}",
        f"Generated: {timestamp}",
        f"Rows: {summary['rows']}",
        f"Columns: {', '.join(summary['columns']) or '(none)'}",
        "",
        "Statistics snapshot (JSON):",
        json.dumps(summary["stats"], indent=2),
    ]
    text_path.write_text("\n".join(lines), encoding="utf-8")

    summary["report_paths"] = {"json": str(json_path), "text": str(text_path)}
    return summary


def run_garmin_pipeline(ensure_download: bool = False) -> Dict[str, object]:
    """Main orchestrator for Garmin data ingestion and reporting."""
    state = _load_state()
    download_summary: Optional[Dict[str, object]] = None
    if ensure_download:
        download_summary = run_garmin_download()

    pending = detect_new_files(state)
    completed, errors = [], []
    for filename in pending:
        file_path = GARMIN_DATA_PATH / filename
        try:
            df = load_csv(file_path)
            report = generate_report(df, filename)
            completed.append(report)
            state.setdefault("processed", {})[filename] = {
                "sha256": _hash_file(file_path),
                "last_processed": datetime.now().isoformat(),
                "reports": report.get("report_paths", {}),
            }
        except Exception as exc:
            errors.append({"file": filename, "error": str(exc)})

    state["last_run"] = datetime.now().isoformat()
    _save_state(state)
    result = {
        "completed_reports": len(completed),
        "pending_files": len(pending),
        "errors": errors,
        "details": completed,
        "state_file": str(GARMIN_STATE_FILE),
    }
    if download_summary is not None:
        result["download"] = download_summary
    return result
