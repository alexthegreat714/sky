import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore


CONFIG_PATH = Path(__file__).with_name("config.json")
DEFAULT_STATUS_DIR = Path(__file__).resolve().parents[2] / "open-webui-full" / "backend" / "data" / "sky_watchdog"


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sky Watchdog")
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="Priority service name to skip (case-insensitive). Can be used multiple times or comma-separated.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Restrict checks to these priority service names (case-insensitive). Can be used multiple times.",
    )
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM endpoint checks.")
    parser.add_argument("--no-ping", action="store_true", help="Skip ping/ICMP checks.")
    parser.add_argument("--no-garmin", action="store_true", help="Skip Garmin CSV presence check.")
    return parser.parse_args(argv)


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    latency_ms: Optional[int] = None
    when: str = datetime.now(timezone.utc).isoformat()
    priority: int = 0
    retry_count: int = 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_service_name(name: str) -> str:
    return name.strip().lower()


def _load_config() -> Dict[str, Any]:
    # Minimal default config; user can edit config.json next to this script
    default_cfg: Dict[str, Any] = {
        "memory_file": str(
            Path(__file__).resolve().parents[2]
            / "open-webui-full" / "backend" / "data" / "sky_memory.txt"
        ),
        "log_file": str(Path(__file__).with_name("watchdog_log.txt")),
        "status_json": str(DEFAULT_STATUS_DIR / "status.json"),
        "check_interval_seconds": 180,
        "priority_services": [],
        "llm_endpoints": [],
        "ping_hosts": ["8.8.8.8", "1.1.1.1"],
        "daily_summary_hour_utc": 9,
        "garmin": {
            "downloads_dir": str(
                Path.home() / "Desktop" / "Engineering" / "Sky" / "downloads" / "garmin"
            )
        },
    }

    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(default_cfg, indent=2), encoding="utf-8")
        return default_cfg
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return default_cfg


def _ensure_dirs(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _log_append(log_file: Path, line: str) -> None:
    _ensure_dirs(log_file)
    with log_file.open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"{_now_iso()} | {line}\n")


def _append_memory(memory_file: Path, line: str) -> None:
    _ensure_dirs(memory_file)
    with memory_file.open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Sky Watchdog: {line}\n---\n")


def _run_cmd(cmd: List[str], cwd: Optional[str] = None, timeout: int = 60) -> Tuple[int, str, str]:
    if not cmd:
        return (0, "(no-op)", "")
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return (proc.returncode, proc.stdout.strip(), proc.stderr.strip())
    except Exception as e:
        return (-1, "", f"Exception: {e}")


def check_http(name: str, url: str, method: str = "GET", body: Optional[Dict[str, Any]] = None, timeout: int = 6) -> CheckResult:
    if requests is None:
        return CheckResult(name=name, ok=False, detail="requests not installed")
    t0 = time.perf_counter()
    try:
        if method.upper() == "POST":
            r = requests.post(url, json=body or {}, timeout=timeout)
        else:
            r = requests.get(url, timeout=timeout)
        latency = int((time.perf_counter() - t0) * 1000)
        ok = (200 <= r.status_code < 400)
        detail = f"status={r.status_code}"
        return CheckResult(name=name, ok=ok, detail=detail, latency_ms=latency)
    except Exception as e:
        latency = int((time.perf_counter() - t0) * 1000)
        return CheckResult(name=name, ok=False, detail=f"error={e}", latency_ms=latency)


def check_llm_ep(ep: Dict[str, Any]) -> CheckResult:
    ep_type = ep.get("type", "openai")
    url = ep.get("url", "")
    model = ep.get("model", "auto")
    name = f"llm:{ep_type}"
    if requests is None:
        return CheckResult(name=name, ok=False, detail="requests not installed")
    t0 = time.perf_counter()
    try:
        if ep_type == "ollama_generate":
            payload = {"model": model, "prompt": "ping", "stream": False}
            r = requests.post(url, json=payload, timeout=10)
            ok = (200 <= r.status_code < 400)
        elif ep_type == "ollama_chat":
            payload = {"model": model, "messages": [{"role": "user", "content": "ping"}], "stream": False}
            r = requests.post(url, json=payload, timeout=10)
            ok = (200 <= r.status_code < 400)
        else:  # openai-style
            payload = {"model": model, "messages": [{"role": "user", "content": "ping"}]}
            r = requests.post(url, json=payload, timeout=10)
            ok = (200 <= r.status_code < 400)
        latency = int((time.perf_counter() - t0) * 1000)
        return CheckResult(name=name, ok=ok, detail=f"status={r.status_code}", latency_ms=latency)
    except Exception as e:
        latency = int((time.perf_counter() - t0) * 1000)
        return CheckResult(name=name, ok=False, detail=f"error={e}", latency_ms=latency)


def ping_host(host: str, count: int = 1, timeout_sec: int = 4) -> CheckResult:
    name = f"ping:{host}"
    # Windows ping uses -n for count, -w timeout(ms)
    cmd = ["ping", host, "-n", str(count), "-w", str(timeout_sec * 1000)]
    rc, out, err = _run_cmd(cmd, timeout=timeout_sec + 2)
    ok = rc == 0
    detail = out.splitlines()[-1] if out else (err or "no output")
    return CheckResult(name=name, ok=ok, detail=detail)


def check_priority_service(service: Dict[str, Any], log_file: Path, memory_file: Path, retry_state: Dict[str, Dict[str, Any]]) -> List[CheckResult]:
    """Check a priority service and attempt restart if down."""
    results: List[CheckResult] = []
    name = service.get("name", "service")
    url = service.get("url")
    priority = service.get("priority", 99)
    timeout = service.get("timeout_sec", 6)

    # Initialize retry state for this service if not exists
    if name not in retry_state:
        retry_state[name] = {
            "retry_count": 0,
            "last_failure": None,
            "backoff_until": None
        }

    state = retry_state[name]

    # Check if we're in backoff period
    if state["backoff_until"]:
        if datetime.now(timezone.utc) < state["backoff_until"]:
            _log_append(log_file, f"Service {name} in backoff until {state['backoff_until'].isoformat()}")
            return []  # Skip check during backoff
        else:
            # Backoff period expired, reset
            state["backoff_until"] = None

    # Probe the service
    if not url:
        return [CheckResult(name=name, ok=False, detail="no URL configured", priority=priority)]

    probe_result = check_http(f"probe:{name}", url, timeout=timeout)
    probe_result.priority = priority
    probe_result.retry_count = state["retry_count"]
    results.append(probe_result)

    if probe_result.ok:
        # Service is up, reset retry state
        if state["retry_count"] > 0:
            _log_append(log_file, f"Service {name} recovered after {state['retry_count']} retries")
            if priority == 1:  # Critical service
                _append_memory(memory_file, f"CRITICAL: {name} recovered after {state['retry_count']} restart attempts")
        state["retry_count"] = 0
        state["last_failure"] = None
        state["backoff_until"] = None
        return results

    # Service is down, attempt restart
    _log_append(log_file, f"Service {name} (priority {priority}) is DOWN: {probe_result.detail}")

    max_retries = service.get("max_retries", 3)
    retry_backoff = service.get("retry_backoff_minutes", [5, 10, 15])

    if state["retry_count"] >= max_retries:
        _log_append(log_file, f"Service {name} exceeded max retries ({max_retries}), giving up")
        if priority == 1:  # Critical service
            _append_memory(memory_file, f"CRITICAL: {name} failed after {max_retries} restart attempts - MANUAL INTERVENTION REQUIRED")
        return results

    # Attempt restart
    restart_cmd = service.get("restart_cmd") or []
    workdir = service.get("working_dir") or None
    post_wait = service.get("post_restart_wait_sec", 10)

    if restart_cmd:
        _log_append(log_file, f"Attempting restart #{state['retry_count'] + 1} for {name}: {' '.join(restart_cmd)}")
        rc, out, err = _run_cmd(restart_cmd, cwd=workdir, timeout=120)
        _log_append(log_file, f"Restart command rc={rc} out={out[:200]} err={err[:200]}")

        # Wait for service to stabilize
        time.sleep(post_wait)

        # Re-check
        verify_result = check_http(f"verify:{name}", url, timeout=timeout)
        verify_result.priority = priority
        verify_result.retry_count = state["retry_count"] + 1
        results.append(verify_result)

        if verify_result.ok:
            _log_append(log_file, f"Service {name} restarted successfully")
            state["retry_count"] = 0
            state["last_failure"] = None
            state["backoff_until"] = None
            if priority == 1:  # Critical service
                _append_memory(memory_file, f"CRITICAL: {name} was down but successfully restarted")
        else:
            # Restart failed, update retry state and set backoff
            state["retry_count"] += 1
            state["last_failure"] = datetime.now(timezone.utc)

            # Calculate backoff time
            backoff_idx = min(state["retry_count"] - 1, len(retry_backoff) - 1)
            backoff_minutes = retry_backoff[backoff_idx]
            state["backoff_until"] = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)

            _log_append(log_file, f"Service {name} restart failed (attempt {state['retry_count']}/{max_retries}), backing off for {backoff_minutes} minutes")

            if priority == 1:  # Critical service
                _append_memory(memory_file, f"CRITICAL: {name} restart attempt {state['retry_count']} FAILED - will retry in {backoff_minutes} minutes")
    else:
        _log_append(log_file, f"No restart command configured for {name}")

    return results


def write_status(status_path: Path, payload: Dict[str, Any]) -> None:
    _ensure_dirs(status_path)
    status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def daily_summary_due(status_path: Path) -> bool:
    # simple check: write one summary per UTC date
    stamp_path = status_path.parent / "last_summary_utc.txt"
    today = date.today().isoformat()
    if not stamp_path.exists():
        stamp_path.write_text(today, encoding="utf-8")
        return True
    prev = stamp_path.read_text(encoding="utf-8").strip()
    if prev != today:
        stamp_path.write_text(today, encoding="utf-8")
        return True
    return False


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    cfg = _load_config()
    log_file = Path(cfg.get("log_file", str(Path(__file__).with_name("watchdog_log.txt"))))
    status_path = Path(cfg.get("status_json", str(DEFAULT_STATUS_DIR / "status.json")))
    memory_file = Path(cfg.get("memory_file", ""))

    _ensure_dirs(status_path)
    _ensure_dirs(log_file)

    results: List[CheckResult] = []

    # Persistent retry state (in-memory for now; could be persisted to file)
    retry_state: Dict[str, Dict[str, Any]] = {}

    env_skip = os.getenv("SKY_WATCHDOG_SKIP", "")
    skip_names: List[str] = []
    for raw in args.skip:
        skip_names.extend([part.strip() for part in raw.split(",") if part.strip()])
    if env_skip:
        skip_names.extend([part.strip() for part in env_skip.split(",") if part.strip()])
    skip_set = {_normalize_service_name(name) for name in skip_names}
    only_set = {_normalize_service_name(name) for name in (args.only or []) if name}

    if skip_set:
        _log_append(log_file, f"Skipping services (CLI/env): {', '.join(sorted(skip_names))}")
    if only_set:
        _log_append(log_file, f"Restricting services to: {', '.join(sorted(only_set))}")

    # Check priority services (Code, OWUI, Chess)
    for service in cfg.get("priority_services", []) or []:
        raw_name = service.get("name", "service")
        norm_name = _normalize_service_name(raw_name)

        if only_set and norm_name not in only_set:
            continue

        if norm_name in skip_set:
            _log_append(log_file, f"Service {raw_name} skipped via CLI/env configuration")
            results.append(
                CheckResult(
                    name=raw_name,
                    ok=True,
                    detail="skipped",
                    priority=service.get("priority", 0),
                )
            )
            continue

        service_results = check_priority_service(service, log_file, memory_file, retry_state)
        results.extend(service_results)

    # LLM endpoints (optional checks)
    if not args.no_llm:
        for ep in cfg.get("llm_endpoints", []) or []:
            results.append(check_llm_ep(ep))

    # Ping checks (connectivity)
    if not args.no_ping:
        for host in cfg.get("ping_hosts", []) or []:
            results.append(ping_host(host))

    # Garmin CSV presence check (yesterday)
    if not args.no_garmin:
        try:
            gar = cfg.get("garmin") or {}
            ddir = Path(gar.get("downloads_dir")) if gar.get("downloads_dir") else None
            if ddir and ddir.exists():
                y = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
                prefix = f"sleep-{y}-"
                found = []
                for p in ddir.glob(f"{prefix}*.csv"):
                    try:
                        sz = p.stat().st_size
                        found.append((p.name, sz))
                    except Exception:
                        continue
                if found:
                    name, sz = sorted(found, key=lambda t: t[1], reverse=True)[0]
                    results.append(CheckResult(name="garmin:csv:yesterday", ok=True, detail=f"{name} size={sz}"))
                else:
                    results.append(CheckResult(name="garmin:csv:yesterday", ok=False, detail="missing"))
            else:
                results.append(CheckResult(name="garmin:csv:config", ok=False, detail="downloads_dir not set or missing"))
        except Exception as e:
            results.append(CheckResult(name="garmin:csv:error", ok=False, detail=str(e)))

    payload: Dict[str, Any] = {
        "when": _now_iso(),
        "results": [asdict(r) for r in results],
        "retry_state": {
            name: {
                "retry_count": state["retry_count"],
                "last_failure": state["last_failure"].isoformat() if state["last_failure"] else None,
                "backoff_until": state["backoff_until"].isoformat() if state["backoff_until"] else None
            }
            for name, state in retry_state.items()
        }
    }
    write_status(status_path, payload)

    # Log a once-per-day compact summary to Sky memory
    if daily_summary_due(status_path):
        ok = sum(1 for r in results if r.ok)
        total = len(results)
        bad = total - ok

        # Separate critical failures
        critical_failures = [r for r in results if not r.ok and r.priority == 1]
        if critical_failures:
            crit_names = ", ".join([r.name for r in critical_failures])
            brief = f"⚠️ CRITICAL FAILURES: {crit_names} | Total checks: {ok}/{total} OK, {bad} issues"
        else:
            brief = f"Watchdog summary: {ok}/{total} checks OK, {bad} issues. Status: {status_path}"

        try:
            _append_memory(memory_file, brief)
        except Exception as e:
            _log_append(log_file, f"Failed to append summary to memory: {e}")

    # Also append to watchdog log
    for r in results:
        priority_str = f"[P{r.priority}]" if r.priority > 0 else ""
        retry_str = f"[retry:{r.retry_count}]" if r.retry_count > 0 else ""
        _log_append(log_file, f"{priority_str}{retry_str} {r.name} | ok={r.ok} | {r.detail} | {r.latency_ms}ms")

    # return non-zero if any critical service failed
    critical_failed = any(not r.ok and r.priority == 1 for r in results)
    return 1 if critical_failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
