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

# === Paths ===
CONFIG_PATH = Path(__file__).with_name("config.json")
DEFAULT_STATUS_DIR = (
    Path(__file__).resolve().parents[2]
    / "open-webui-full" / "backend" / "data" / "sky_watchdog"
)

# ---------------------------
# CLI
# ---------------------------
def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sky / Aegis Watchdog")
    p.add_argument("--skip", action="append", default=[], help="Skip these services (name, case-insensitive). Can be repeated or comma-separated.")
    p.add_argument("--only", action="append", default=[], help="Only check these services (name, case-insensitive).")
    p.add_argument("--no-llm", action="store_true", help="Skip LLM endpoint checks.")
    p.add_argument("--no-ping", action="store_true", help="Skip ping/ICMP checks.")
    p.add_argument("--no-garmin", action="store_true", help="Skip Garmin CSV presence check.")
    return p.parse_args(argv)

# ---------------------------
# Models
# ---------------------------
@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    latency_ms: Optional[int] = None
    when: str = datetime.now(timezone.utc).isoformat()
    priority: int = 0
    retry_count: int = 0

# ---------------------------
# Utils
# ---------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _normalize(name: str) -> str:
    return name.strip().lower()

def _ensure_dirs(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def _run(cmd: List[str], cwd: Optional[str] = None, timeout: int = 60) -> Tuple[int, str, str]:
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

def _log_append(log_file: Path, line: str) -> None:
    _ensure_dirs(log_file)
    with log_file.open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"{_now_iso()} | {line}\n")

def _append_memory(memory_file: Path, line: str) -> None:
    _ensure_dirs(memory_file)
    with memory_file.open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Watchdog: {line}\n---\n")

# ---------------------------
# Config
# ---------------------------
def _load_config() -> Dict[str, Any]:
    default_cfg: Dict[str, Any] = {
        "memory_file": str(
            Path(__file__).resolve().parents[2]
            / "open-webui-full" / "backend" / "data" / "sky_memory.txt"
        ),
        "log_file": str(Path(__file__).with_name("watchdog_log.txt")),
        "status_json": str(DEFAULT_STATUS_DIR / "status.json"),
        "check_interval_seconds": 180,

        # Services we actively manage (restart if down)
        "priority_services": [
            # OWUI (port 3000)
            {
                "name": "openwebui",
                "priority": 1,
                "url": "http://127.0.0.1:3000/_app/immutable/entry/start.CDB-sKN8.js",
                "timeout_sec": 6,
                "max_retries": 3,
                "retry_backoff_minutes": [5, 10, 15],
                "restart_cmd": [
                    "cmd", "/c",
                    r"C:\Users\blyth\Desktop\Engineering\open-webui-full\autoboot-chat-only.bat"
                ],
                "working_dir": r"C:\Users\blyth\Desktop\Engineering\open-webui-full",
                "post_restart_wait_sec": 12
            },
            # Chess (port 5000) — non-critical by default
            {
                "name": "chess",
                "priority": 2,
                "url": "http://127.0.0.1:5000/",
                "timeout_sec": 5,
                "max_retries": 2,
                "retry_backoff_minutes": [5, 10],
                "restart_cmd": [
                    "cmd", "/c",
                    r"C:\Users\blyth\Desktop\Engineering\Chess\autoboot-chess-only.bat"
                ],
                "working_dir": r"C:\Users\blyth\Desktop\Engineering\Chess",
                "post_restart_wait_sec": 8
            },
        ],

        # ETag parity checks (prove Cloudflare serves current assets)
        "etag_pairs": [
            {
                "name": "etag:openwebui",
                "local":  "http://127.0.0.1:3000/_app/immutable/entry/start.CDB-sKN8.js",
                "public": "https://chat.alex-blythe.com/_app/immutable/entry/start.CDB-sKN8.js",
                "cache_bust": True
            }
        ],

        # Cloudflared tunnel checks
        "tunnels": [
            {
                "name": "tunnel:chat",
                "tunnel_name": "sky-tunnel",
                "config_path": r"C:\Users\blyth\.cloudflared\config.yml"
            },
            {
                "name": "tunnel:chess",
                "tunnel_name": "chess-tunnel",
                "config_path": r"C:\Users\blyth\.cloudflared\config-chess.yml"
            }
        ],

        # Optional checks
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

# ---------------------------
# HTTP & ETag
# ---------------------------
def check_http(name: str, url: str, timeout: int = 6, headers: Optional[Dict[str, str]] = None) -> CheckResult:
    if requests is None:
        return CheckResult(name=name, ok=False, detail="requests not installed")
    t0 = time.perf_counter()
    try:
        r = requests.get(url, timeout=timeout, headers=headers or {})
        latency = int((time.perf_counter() - t0) * 1000)
        ok = (200 <= r.status_code < 400)
        return CheckResult(name=name, ok=ok, detail=f"status={r.status_code}", latency_ms=latency)
    except Exception as e:
        latency = int((time.perf_counter() - t0) * 1000)
        return CheckResult(name=name, ok=False, detail=f"error={e}", latency_ms=latency)

def get_etag(url: str, cache_bust: bool = False, timeout: int = 6) -> Tuple[bool, Optional[str], str]:
    if requests is None:
        return (False, None, "requests not installed")
    headers = {}
    if cache_bust:
        headers["Cache-Control"] = "no-cache"
    try:
        r = requests.head(url, timeout=timeout, headers=headers)
        if r.status_code >= 400:
            # Some setups don’t return HEAD; fall back to GET without body cost
            r = requests.get(url, timeout=timeout, headers=headers, stream=True)
        etag = r.headers.get("etag")
        return (200 <= r.status_code < 400, etag, f"status={r.status_code}")
    except Exception as e:
        return (False, None, f"error={e}")

def check_etag_pair(name: str, local_url: str, public_url: str, cache_bust: bool) -> CheckResult:
    okL, eLocal, dL = get_etag(local_url, cache_bust=cache_bust)
    okP, ePub, dP   = get_etag(public_url, cache_bust=cache_bust)
    if not okL or not okP:
        return CheckResult(name=name, ok=False, detail=f"local({dL}) public({dP})")
    if not eLocal or not ePub:
        return CheckResult(name=name, ok=False, detail=f"etag missing: local={eLocal} public={ePub}")
    return CheckResult(name=name, ok=(eLocal == ePub), detail=f"etag local={eLocal} public={ePub}")

# ---------------------------
# Tunnels
# ---------------------------
def check_tunnel(name: str, tunnel_name: str, config_path: str) -> CheckResult:
    # 1) config file exists
    if not Path(config_path).exists():
        return CheckResult(name=name, ok=False, detail=f"missing config: {config_path}")

    # 2) cloudflared tunnel info <name> exits 0
    rc, out, err = _run(["cloudflared", "tunnel", "info", tunnel_name], timeout=20)
    if rc != 0:
        return CheckResult(name=name, ok=False, detail=f"tunnel info failed rc={rc} err={err[:140]}")

    # Heuristic: show connector lines present
    if "CONNECTOR ID" in out or "Connector ID" in out:
        return CheckResult(name=name, ok=True, detail="info OK (connectors present)")
    return CheckResult(name=name, ok=True, detail="info OK")

# ---------------------------
# Pings / LLM
# ---------------------------
def ping_host(host: str, count: int = 1, timeout_sec: int = 4) -> CheckResult:
    name = f"ping:{host}"
    cmd = ["ping", host, "-n", str(count), "-w", str(timeout_sec * 1000)]
    rc, out, err = _run(cmd, timeout=timeout_sec + 3)
    ok = rc == 0
    tail = out.splitlines()[-1] if out else (err or "no output")
    return CheckResult(name=name, ok=ok, detail=tail)

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
        elif ep_type == "ollama_chat":
            payload = {"model": model, "messages": [{"role": "user", "content": "ping"}], "stream": False}
            r = requests.post(url, json=payload, timeout=10)
        else:
            payload = {"model": model, "messages": [{"role": "user", "content": "ping"}]}
            r = requests.post(url, json=payload, timeout=10)
        lat = int((time.perf_counter() - t0) * 1000)
        return CheckResult(name=name, ok=(200 <= r.status_code < 400), detail=f"status={r.status_code}", latency_ms=lat)
    except Exception as e:
        lat = int((time.perf_counter() - t0) * 1000)
        return CheckResult(name=name, ok=False, detail=f"error={e}", latency_ms=lat)

# ---------------------------
# Service check + restart with backoff
# ---------------------------
def check_priority_service(service: Dict[str, Any],
                           log_file: Path,
                           memory_file: Path,
                           retry_state: Dict[str, Dict[str, Any]]) -> List[CheckResult]:
    out: List[CheckResult] = []
    name = service.get("name", "service")
    url = service.get("url")
    priority = service.get("priority", 99)
    timeout_sec = service.get("timeout_sec", 6)

    state = retry_state.setdefault(name, {
        "retry_count": 0,
        "last_failure": None,
        "backoff_until": None
    })

    # respect backoff
    if state["backoff_until"] and datetime.now(timezone.utc) < state["backoff_until"]:
        _log_append(log_file, f"{name} in backoff until {state['backoff_until'].isoformat()}")
        return out

    if not url:
        out.append(CheckResult(name=name, ok=False, detail="no URL configured", priority=priority))
        return out

    probe = check_http(f"probe:{name}", url, timeout=timeout_sec)
    probe.priority = priority
    probe.retry_count = state["retry_count"]
    out.append(probe)

    if probe.ok:
        if state["retry_count"] > 0:
            _log_append(log_file, f"{name} recovered after {state['retry_count']} retries")
            if priority == 1:
                _append_memory(memory_file, f"CRITICAL RECOVERY: {name} recovered after {state['retry_count']} retries")
        state["retry_count"] = 0
        state["last_failure"] = None
        state["backoff_until"] = None
        return out

    # down → attempt restart via provided .bat / command
    _log_append(log_file, f"{name} DOWN: {probe.detail}")
    max_retries = service.get("max_retries", 3)
    backoff_list = service.get("retry_backoff_minutes", [5, 10, 15])

    if state["retry_count"] >= max_retries:
        _log_append(log_file, f"{name} exceeded max retries ({max_retries}); manual intervention")
        if priority == 1:
            _append_memory(memory_file, f"CRITICAL: {name} failed after {max_retries} attempts — manual intervention required")
        return out

    restart_cmd = service.get("restart_cmd") or []
    workdir = service.get("working_dir") or None
    wait_after = service.get("post_restart_wait_sec", 10)

    if restart_cmd:
        _log_append(log_file, f"Restarting {name} (attempt {state['retry_count']+1}): {' '.join(restart_cmd)}")
        rc, ro, re = _run(restart_cmd, cwd=workdir, timeout=120)
        _log_append(log_file, f"rc={rc} out={ro[:200]} err={re[:200]}")
        time.sleep(wait_after)

        verify = check_http(f"verify:{name}", url, timeout=timeout_sec)
        verify.priority = priority
        verify.retry_count = state["retry_count"] + 1
        out.append(verify)

        if verify.ok:
            _log_append(log_file, f"{name} restart successful")
            state["retry_count"] = 0
            state["last_failure"] = None
            state["backoff_until"] = None
            if priority == 1:
                _append_memory(memory_file, f"CRITICAL: {name} was down but successfully restarted")
        else:
            state["retry_count"] += 1
            state["last_failure"] = datetime.now(timezone.utc)
            idx = min(state["retry_count"] - 1, len(backoff_list) - 1)
            mins = backoff_list[idx]
            state["backoff_until"] = datetime.now(timezone.utc) + timedelta(minutes=mins)
            _log_append(log_file, f"{name} restart failed; backoff {mins} min")
            if priority == 1:
                _append_memory(memory_file, f"CRITICAL: {name} restart attempt {state['retry_count']} failed; backoff {mins} min")
    else:
        _log_append(log_file, f"{name} has no restart_cmd configured")

    return out

# ---------------------------
# Daily summary stamp
# ---------------------------
def write_status(status_path: Path, payload: Dict[str, Any]) -> None:
    _ensure_dirs(status_path)
    status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def daily_summary_due(status_path: Path) -> bool:
    stamp = status_path.parent / "last_summary_utc.txt"
    today = date.today().isoformat()
    if not stamp.exists():
        stamp.write_text(today, encoding="utf-8")
        return True
    prev = stamp.read_text(encoding="utf-8").strip()
    if prev != today:
        stamp.write_text(today, encoding="utf-8")
        return True
    return False

# ---------------------------
# Main
# ---------------------------
def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    cfg = _load_config()

    log_file = Path(cfg.get("log_file", str(Path(__file__).with_name("watchdog_log.txt"))))
    status_path = Path(cfg.get("status_json", str(DEFAULT_STATUS_DIR / "status.json")))
    memory_file = Path(cfg.get("memory_file", ""))

    _ensure_dirs(log_file)
    _ensure_dirs(status_path)

    results: List[CheckResult] = []
    retry_state: Dict[str, Dict[str, Any]] = {}

    # skip/only sets
    env_skip = os.getenv("SKY_WATCHDOG_SKIP", "")
    skip: List[str] = []
    for raw in args.skip:
        skip.extend([x.strip() for x in raw.split(",") if x.strip()])
    if env_skip:
        skip.extend([x.strip() for x in env_skip.split(",") if x.strip()])
    skip_set = {_normalize(x) for x in skip}
    only_set = {_normalize(x) for x in (args.only or []) if x}

    if skip_set:
        _log_append(log_file, f"Skip: {', '.join(sorted(skip_set))}")
    if only_set:
        _log_append(log_file, f"Only: {', '.join(sorted(only_set))}")

    # Priority services (restartable)
    for svc in cfg.get("priority_services", []) or []:
        raw = svc.get("name", "service")
        nm = _normalize(raw)
        if only_set and nm not in only_set:
            continue
        if nm in skip_set:
            _log_append(log_file, f"Skip service {raw}")
            results.append(CheckResult(name=raw, ok=True, detail="skipped", priority=svc.get("priority", 0)))
            continue
        results.extend(check_priority_service(svc, log_file, memory_file, retry_state))

    # ETag parity checks
    for ep in cfg.get("etag_pairs", []) or []:
        nm = ep.get("name", "etag")
        if only_set and _normalize(nm) not in only_set:
            continue
        r = check_etag_pair(
            nm,
            local_url=ep.get("local", ""),
            public_url=ep.get("public", ""),
            cache_bust=bool(ep.get("cache_bust", True)),
        )
        results.append(r)

    # Tunnel checks
    for t in cfg.get("tunnels", []) or []:
        nm = t.get("name", "tunnel")
        if only_set and _normalize(nm) not in only_set:
            continue
        r = check_tunnel(nm, t.get("tunnel_name", ""), t.get("config_path", ""))
        results.append(r)

    # LLM endpoints
    if not args.no_llm:
        for ep in cfg.get("llm_endpoints", []) or []:
            results.append(check_llm_ep(ep))

    # Pings
    if not args.no_ping:
        for host in cfg.get("ping_hosts", []) or []:
            results.append(ping_host(host))

    # Garmin
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

    # Persist status
    payload: Dict[str, Any] = {
        "when": _now_iso(),
        "results": [asdict(r) for r in results],
        "retry_state": {
            k: {
                "retry_count": v["retry_count"],
                "last_failure": v["last_failure"].isoformat() if v["last_failure"] else None,
                "backoff_until": v["backoff_until"].isoformat() if v["backoff_until"] else None
            }
            for k, v in retry_state.items()
        }
    }
    write_status(status_path, payload)

    # Daily memory drop
    if daily_summary_due(status_path):
        ok = sum(1 for r in results if r.ok)
        total = len(results)
        bad = total - ok
        crit = [r for r in results if not r.ok and r.priority == 1]
        if crit:
            names = ", ".join([r.name for r in crit])
            brief = f"⚠️ CRITICAL: {names}. Checks OK {ok}/{total}, issues {bad}."
        else:
            brief = f"Watchdog summary: OK {ok}/{total}, issues {bad}. Status @ {status_path}"
        try:
            _append_memory(memory_file, brief)
        except Exception as e:
            _log_append(log_file, f"memory append fail: {e}")

    # Write log lines per check
    for r in results:
        p = f"[P{r.priority}]" if r.priority else ""
        rc = f"[retry:{r.retry_count}]" if r.retry_count else ""
        _log_append(log_file, f"{p}{rc} {r.name} | ok={r.ok} | {r.detail} | {r.latency_ms}ms")

    # Exit non-zero if any critical failed
    critical_failed = any((not r.ok) and r.priority == 1 for r in results)
    return 1 if critical_failed else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
