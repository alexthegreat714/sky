import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\blyth\Desktop\Engineering")
SKY = ROOT / "Sky"
TOOLS = SKY / "tools"
CLICK_REPLAY = TOOLS / "garmin_click_replay.ps1"
DOWNLOAD_INBOX = SKY / "downloads" / "garmin"
USER_DOWNLOADS = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
REPORTER = SKY / "agents" / "morning_reporter.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sky Morning Orchestrator")
    parser.add_argument(
        "--date",
        type=str,
        help="ISO date (YYYY-MM-DD). Defaults to today unless --yesterday is provided.",
    )
    parser.add_argument("--yesterday", action="store_true", help="Use yesterday's date.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Seconds to wait for the sleep CSV to appear (default: 300).",
    )
    return parser.parse_args()


def resolve_iso(args: argparse.Namespace) -> str:
    if args.date:
        return args.date
    if args.yesterday:
        return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return datetime.now().strftime("%Y-%m-%d")


def run_click_replay(target_iso: str, when_hint: str | None) -> None:
    if when_hint:
        when_flag = when_hint
    else:
        today_iso = datetime.now().strftime("%Y-%m-%d")
        yesterday_iso = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if target_iso == today_iso:
            when_flag = "TODAY"
        elif target_iso == yesterday_iso:
            when_flag = "YESTERDAY"
        else:
            when_flag = target_iso
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(CLICK_REPLAY),
        "-When",
        when_flag,
    ]
    print(f"[run] Starting click replay for {target_iso} …")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        raise RuntimeError(f"Click replay failed with exit code {result.returncode}")


def wait_for_csv(target_iso: str, timeout: int) -> Path:
    pattern = f"sleep-{target_iso}"
    deadline = time.time() + timeout
    print(f"[wait] Watching {USER_DOWNLOADS} for {pattern}*.csv (timeout {timeout}s)")
    while time.time() < deadline:
        for candidate in sorted(USER_DOWNLOADS.glob("sleep-*.csv"), key=lambda p: p.stat().st_mtime, reverse=True):
            if candidate.name.startswith(pattern):
                print(f"[ok] Found download: {candidate}")
                return candidate
        time.sleep(2)
    raise TimeoutError(f"No CSV matching {pattern}* found within {timeout} seconds.")


def stage_csv(source: Path, target_iso: str) -> Path:
    DOWNLOAD_INBOX.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = DOWNLOAD_INBOX / f"sleep-{target_iso}_Sky_{timestamp}.csv"
    shutil.copy2(source, destination)
    print(f"[copy] Saved to {destination}")
    return destination


def run_reporter(target_iso: str) -> None:
    env = os.environ.copy()
    env["SKY_GARMIN_TARGET_DATE"] = target_iso
    cmd = [sys.executable, str(REPORTER)]
    print("[run] Executing morning_reporter.py …")
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"morning_reporter.py exited with {result.returncode}")


def main() -> None:
    args = parse_args()
    target_iso = resolve_iso(args)
    when_hint = None
    if args.date:
        when_hint = args.date
    elif args.yesterday:
        when_hint = "YESTERDAY"
    run_click_replay(target_iso, when_hint)
    csv_path = wait_for_csv(target_iso, args.timeout)
    stage_csv(csv_path, target_iso)
    run_reporter(target_iso)
    print("[done] Morning orchestrator complete.")


if __name__ == "__main__":
    main()
