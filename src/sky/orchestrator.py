"""
Sky Orchestrator v1 (scaffold):
- Loads config + schedule
- Enforces authority before tool execution
- Routes simple tasks (heartbeat, memory rotate check, tool chains)
- Writes status for external watchers
- Exposes programmatic hooks used by service.py
"""
from pathlib import Path
import time, datetime as dt, json
from typing import Dict, Any, List

from .utils import load_config
from .status import write_heartbeat, write_last_action
from .scheduler import SimpleScheduler

# Optional imports (exist in Phase 2/3 scaffolds)
def _safe_import(path, name):
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None

check_authority = _safe_import("src.governance.authority_gate", "check_authority")
refusal_message = _safe_import("src.governance.authority_gate", "refusal_message")
remember_short = _safe_import("src.memory.manager", "remember_short")
remember_long_export = _safe_import("src.memory.manager", "remember_long_export")
rag_query = _safe_import("src.rag.query", "query")
memory_promoter_run = _safe_import("src.memory.promoter", "run_once")
senate_publish_json = _safe_import("src.senate_bus.broker", "publish_json")

# Tool registry (new unified tool execution)
from .tool_registry import list_tools, execute_tool as run_tool

class SkyOrchestrator:
    def __init__(self):
        self.cfg = load_config() or {}
        self.scheduler = SimpleScheduler()
        self.loaded = False

    def load(self):
        # schedule
        sched_yaml = Path("src/sky/schedule.yaml")
        sch = {}
        if sched_yaml.exists():
            import yaml
            sch = yaml.safe_load(sched_yaml.read_text(encoding="utf-8")) or {}
        # daily
        for item in sch.get("daily", []):
            self.scheduler.add_daily(item["name"], item["time"], lambda n=item["name"]: self.handle_task(n))
        # every-N
        for item in sch.get("every", []):
            self.scheduler.add_every_minutes(item["name"], item["minutes"], lambda n=item["name"]: self.handle_task(n))
        self.loaded = True

    def authority_ok(self, action: str) -> bool:
        if callable(check_authority):
            return bool(check_authority(action))
        # default allow basic actions; conservative for risky actions
        restricted_defaults = {"restart_services","modify_system_configs","financial_transactions","self_upgrade"}
        return action not in restricted_defaults

    def _publish_to_senate(self, topic: str, payload: Dict[str, Any]):
        """Publish message to senate bus (if available)"""
        if callable(senate_publish_json):
            try:
                senate_publish_json(topic, payload)
            except Exception:
                pass  # Senate bus not critical for operation

    def handle_task(self, name: str):
        # Extend here with more branches; this keeps v1 readable.
        if name == "heartbeat":
            write_heartbeat({"orchestrator":"running"})
            write_last_action("heartbeat")
            return {"ok": True}

        if name == "memory_rotate_check":
            # Run memory promotion pipeline
            if callable(memory_promoter_run):
                result = memory_promoter_run()
                write_last_action("memory_rotate_check", result)
                return result
            else:
                write_last_action("memory_rotate_check", {"note":"promoter not available"})
                return {"ok": True}

        if name == "garmin_pull":
            result = self._run_named_tool_chain(
                chain_name="garmin_pull",
                steps=[("run_approved_tools", "morning_garmin_downloader", ["--yesterday"])],
            )
            # Publish to senate bus if successful
            if result.get("ok"):
                self._publish_to_senate("daily.data_ready", {
                    "source": "sky",
                    "task": "garmin_pull",
                    "status": "completed",
                    "timestamp": time.time()
                })
            return result

        if name == "morning_report":
            return self._run_named_tool_chain(
                chain_name="morning_report",
                steps=[
                    ("run_approved_tools", "morning_reporter", ["--today"]),
                    ("run_approved_tools", "tts_morning_cli", ["--input", "sky_daily/today.json"]),
                ],
            )

        # Unknown task -> log only
        write_last_action("unknown_task", {"name": name})
        return {"ok": False, "error": f"unknown task: {name}"}

    def _run_named_tool_chain(self, chain_name: str, steps: List):
        """steps: list of tuples (required_action, tool_name, args_list)"""
        results = []
        for required, tool, args in steps:
            if not self.authority_ok(required):
                msg = required
                if callable(refusal_message):
                    msg = refusal_message(required)
                write_last_action("authority_block", {"required": required, "tool": tool, "msg": msg})
                return {"ok": False, "blocked": required, "tool": tool, "message": msg}

            out = run_tool(tool, args=args)
            results.append({"tool": tool, "result": out})
            if not out.get("ok", False):
                write_last_action("tool_failed", {"tool": tool, "stderr": out.get("stderr")})
                return {"ok": False, "failed_tool": tool, "results": results}

        write_last_action("chain_ok", {"chain": chain_name, "steps": [s[1] for s in steps]})
        return {"ok": True, "results": results}

    def loop(self, stop_after_seconds: int = None):
        if not self.loaded:
            self.load()
        start = time.time()
        while True:
            now = dt.datetime.now()
            self.scheduler.tick(now)
            time.sleep(1)
            if stop_after_seconds and (time.time() - start) >= stop_after_seconds:
                break

# singleton getter used by service
_ORCH = None
def get_orchestrator() -> SkyOrchestrator:
    global _ORCH
    if _ORCH is None:
        _ORCH = SkyOrchestrator()
        _ORCH.load()
    return _ORCH
