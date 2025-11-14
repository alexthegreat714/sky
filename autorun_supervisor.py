import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from mss import mss

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from garmin_pipeline import detect_new_files, run_garmin_pipeline  # type: ignore
else:
    from .garmin_pipeline import detect_new_files, run_garmin_pipeline


class AutoRunSupervisor:
    """Nightly proof runner for the Sky Garmin data pipeline."""

    EVIDENCE_DIR = Path(r"C:\Users\blyth\Desktop\Engineering\rag_data\Sky\logs\autorun_evidence")
    STATE_FILE = EVIDENCE_DIR / "garmin_autorun_state.json"

    def __init__(self) -> None:
        self.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        self.state: Dict[str, object] = self._load_state()

    def _load_state(self) -> Dict[str, object]:
        if self.STATE_FILE.exists():
            try:
                return json.loads(self.STATE_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {"history": [], "last_run": None, "last_pending": [], "last_result": {}}

    def _save_state(self) -> None:
        self.STATE_FILE.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def _capture_screenshot(self, stamp: str) -> Path:
        screenshot_path = self.EVIDENCE_DIR / f"garmin_{stamp}.png"
        with mss() as capture:
            capture.shot(output=str(screenshot_path))
        return screenshot_path

    def _write_summary(self, stamp: str, pending: List[str], result: Dict[str, object]) -> Path:
        summary_path = self.EVIDENCE_DIR / f"garmin_{stamp}.txt"
        lines = [
            f"Sky Garmin Nightly Proof :: {datetime.now().isoformat()}",
            f"Pending CSVs: {', '.join(pending) if pending else 'none detected'}",
            "",
            "Pipeline result:",
            json.dumps(result, indent=2),
        ]
        summary_path.write_text("\n".join(lines), encoding="utf-8")
        return summary_path

    def nightly_proof(self) -> Dict[str, object]:
        """Execute the ingestion pipeline silently and capture nightly evidence."""
        pending = detect_new_files()
        result = run_garmin_pipeline()
        stamp = datetime.now().strftime("%Y%m%d")
        screenshot = self._capture_screenshot(stamp)
        summary = self._write_summary(stamp, pending, result)

        record = {
            "timestamp": datetime.now().isoformat(),
            "pending": pending,
            "result": result,
            "summary": str(summary),
            "screenshot": str(screenshot),
        }
        history = self.state.setdefault("history", [])
        history.append(record)
        self.state["history"] = history[-30:]  # keep the most recent entries
        self.state.update({"last_run": record["timestamp"], "last_pending": pending, "last_result": result})
        self._save_state()

        return {"pending": pending, "ran_pipeline": True, "result": result, "summary_path": str(summary), "screenshot_path": str(screenshot)}

    def status(self) -> Dict[str, object]:
        return self.state


if __name__ == "__main__":
    supervisor = AutoRunSupervisor()
    result = supervisor.nightly_proof()
    print(json.dumps(result, indent=2))
