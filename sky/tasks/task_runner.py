"""
Sky Task Runner - Internal scheduler with task queue

Features:
- Async loop with configurable tick interval (default 30s)
- JSON-based task queue (sky/tasks/queue.json)
- Human-readable HH:MM schedule parsing
- Constitutional authority enforcement
- Comprehensive logging
- FastAPI endpoints for task management
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Setup logging
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True, parents=True)
LOG_FILE = LOG_DIR / "task_runner.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
BASE = Path(__file__).resolve().parents[2]
TASK_DIR = BASE / "sky" / "tasks"
QUEUE_FILE = TASK_DIR / "queue.json"

# Safe imports
def _safe_import(path, name):
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None

check_authority = _safe_import("src.governance.authority_gate", "check_authority")
run_tool = _safe_import("src.sky.tool_registry", "run_tool")


class TaskQueue:
    """Manages task queue storage and retrieval"""

    def __init__(self, queue_file: Path = QUEUE_FILE):
        self.queue_file = queue_file
        self._ensure_queue_exists()

    def _ensure_queue_exists(self):
        """Create empty queue if it doesn't exist"""
        if not self.queue_file.exists():
            self.queue_file.parent.mkdir(parents=True, exist_ok=True)
            self._write_queue([])

    def _read_queue(self) -> List[Dict[str, Any]]:
        """Read task queue from JSON file"""
        try:
            with self.queue_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read queue: {e}")
            return []

    def _write_queue(self, tasks: List[Dict[str, Any]]):
        """Write task queue to JSON file"""
        try:
            with self.queue_file.open("w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write queue: {e}")

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks"""
        return self._read_queue()

    def get_task(self, name: str) -> Optional[Dict[str, Any]]:
        """Get task by name"""
        tasks = self._read_queue()
        for task in tasks:
            if task.get("name") == name:
                return task
        return None

    def add_task(self, task: Dict[str, Any]) -> bool:
        """Add new task to queue"""
        tasks = self._read_queue()

        # Check if task already exists
        if any(t.get("name") == task.get("name") for t in tasks):
            logger.warning(f"Task {task.get('name')} already exists")
            return False

        # Validate required fields
        if not task.get("name") or not task.get("action"):
            logger.error("Task missing required fields: name, action")
            return False

        # Set defaults
        task.setdefault("enabled", True)
        task.setdefault("last_run", None)
        task.setdefault("schedule", None)

        tasks.append(task)
        self._write_queue(tasks)
        logger.info(f"Added task: {task.get('name')}")
        return True

    def update_task(self, name: str, updates: Dict[str, Any]) -> bool:
        """Update existing task"""
        tasks = self._read_queue()
        for i, task in enumerate(tasks):
            if task.get("name") == name:
                tasks[i].update(updates)
                self._write_queue(tasks)
                logger.info(f"Updated task: {name}")
                return True
        logger.warning(f"Task not found: {name}")
        return False

    def remove_task(self, name: str) -> bool:
        """Remove task from queue"""
        tasks = self._read_queue()
        original_len = len(tasks)
        tasks = [t for t in tasks if t.get("name") != name]

        if len(tasks) < original_len:
            self._write_queue(tasks)
            logger.info(f"Removed task: {name}")
            return True

        logger.warning(f"Task not found: {name}")
        return False

    def enable_task(self, name: str) -> bool:
        """Enable task"""
        return self.update_task(name, {"enabled": True})

    def disable_task(self, name: str) -> bool:
        """Disable task"""
        return self.update_task(name, {"enabled": False})


class TaskScheduler:
    """Executes scheduled tasks based on queue"""

    def __init__(self, queue: TaskQueue, tick_interval: int = 30):
        self.queue = queue
        self.tick_interval = tick_interval
        self.running = False

    def _check_authority(self, action: str) -> bool:
        """Check if action is allowed by constitution"""
        if callable(check_authority):
            try:
                return bool(check_authority(action))
            except Exception as e:
                logger.error(f"Authority check failed: {e}")
                return False

        # Default: deny risky actions
        restricted = {"restart_services", "modify_system_configs",
                     "financial_transactions", "self_upgrade"}
        return action not in restricted

    def _parse_schedule(self, schedule: str) -> Optional[tuple]:
        """
        Parse HH:MM schedule string
        Returns: (hour, minute) or None if invalid
        """
        if not schedule:
            return None

        try:
            parts = schedule.split(":")
            if len(parts) != 2:
                return None
            hour = int(parts[0])
            minute = int(parts[1])

            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return (hour, minute)
        except Exception:
            pass

        return None

    def _should_run(self, task: Dict[str, Any], now: datetime) -> bool:
        """Check if task should run now"""
        # Must be enabled
        if not task.get("enabled", False):
            return False

        schedule = task.get("schedule")
        if not schedule:
            return False  # No schedule = never auto-run

        parsed = self._parse_schedule(schedule)
        if not parsed:
            logger.warning(f"Invalid schedule for {task.get('name')}: {schedule}")
            return False

        target_hour, target_minute = parsed

        # Check if current time matches schedule
        if now.hour != target_hour or now.minute != target_minute:
            return False

        # Check last_run to avoid duplicate runs within same minute
        last_run = task.get("last_run")
        if last_run:
            try:
                last_run_dt = datetime.fromisoformat(last_run)
                # Don't run if already ran in the last 2 minutes
                if (now - last_run_dt).total_seconds() < 120:
                    return False
            except Exception:
                pass

        return True

    def _execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task"""
        name = task.get("name", "unknown")
        action = task.get("action", "")

        logger.info(f"Executing task: {name}")

        # Check authority
        if not self._check_authority("run_approved_tools"):
            logger.warning(f"Task {name} blocked by constitution")
            return {
                "ok": False,
                "error": "Authority denied by constitution",
                "task": name
            }

        # Parse and execute action
        # Expected format: "run_tool('tool_name')" or "run_tool('tool_name', ['arg1', 'arg2'])"
        try:
            # Simple eval-based execution (safe in controlled environment)
            # In production, use proper action parser
            if action.startswith("run_tool("):
                if callable(run_tool):
                    # Extract tool name from action string
                    # This is a simple parser - in production, use ast.literal_eval
                    import re
                    match = re.match(r"run_tool\('([^']+)'(?:,\s*(\[.+\]))?\)", action)
                    if match:
                        tool_name = match.group(1)
                        args_str = match.group(2)
                        args = json.loads(args_str) if args_str else []

                        result = run_tool(tool_name, args=args)

                        # Update last_run timestamp
                        self.queue.update_task(name, {
                            "last_run": datetime.now().isoformat()
                        })

                        logger.info(f"Task {name} completed: {result.get('ok', False)}")
                        return result
                    else:
                        logger.error(f"Failed to parse action: {action}")
                        return {"ok": False, "error": "Invalid action format"}
                else:
                    logger.error("run_tool not available")
                    return {"ok": False, "error": "run_tool not available"}
            else:
                logger.error(f"Unsupported action type: {action}")
                return {"ok": False, "error": "Unsupported action type"}

        except Exception as e:
            logger.error(f"Task {name} failed: {e}")
            return {"ok": False, "error": str(e), "task": name}

    async def tick(self):
        """Single scheduler tick - check and execute due tasks"""
        now = datetime.now()
        tasks = self.queue.list_tasks()

        for task in tasks:
            if self._should_run(task, now):
                try:
                    result = self._execute_task(task)
                    logger.info(f"Task {task.get('name')} result: {result}")
                except Exception as e:
                    logger.error(f"Error executing task {task.get('name')}: {e}")

    async def run(self):
        """Main scheduler loop"""
        self.running = True
        logger.info(f"Task scheduler starting (tick interval: {self.tick_interval}s)")

        while self.running:
            try:
                await self.tick()
            except Exception as e:
                logger.error(f"Scheduler tick error: {e}")

            await asyncio.sleep(self.tick_interval)

    def stop(self):
        """Stop scheduler loop"""
        self.running = False
        logger.info("Task scheduler stopping")


# FastAPI integration
def create_task_api():
    """Create FastAPI app for task management"""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except ImportError:
        logger.error("FastAPI not available")
        return None

    app = FastAPI(title="Sky Task Runner API")
    queue = TaskQueue()

    class TaskCreate(BaseModel):
        name: str
        schedule: Optional[str] = None
        enabled: bool = True
        action: str

    class TaskUpdate(BaseModel):
        schedule: Optional[str] = None
        enabled: Optional[bool] = None
        action: Optional[str] = None

    @app.get("/tasks/list")
    def list_tasks():
        """List all tasks"""
        return {"tasks": queue.list_tasks()}

    @app.post("/tasks/add")
    def add_task(task: TaskCreate):
        """Add new task"""
        task_dict = task.dict()
        if queue.add_task(task_dict):
            return {"ok": True, "task": task_dict}
        raise HTTPException(status_code=400, detail="Failed to add task")

    @app.post("/tasks/enable")
    def enable_task(name: str):
        """Enable task"""
        if queue.enable_task(name):
            return {"ok": True, "task": name, "enabled": True}
        raise HTTPException(status_code=404, detail="Task not found")

    @app.post("/tasks/disable")
    def disable_task(name: str):
        """Disable task"""
        if queue.disable_task(name):
            return {"ok": True, "task": name, "enabled": False}
        raise HTTPException(status_code=404, detail="Task not found")

    @app.post("/tasks/run_now")
    def run_task_now(name: str):
        """Execute task immediately"""
        task = queue.get_task(name)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        scheduler = TaskScheduler(queue)
        result = scheduler._execute_task(task)
        return result

    @app.delete("/tasks/remove")
    def remove_task(name: str):
        """Remove task"""
        if queue.remove_task(name):
            return {"ok": True, "task": name}
        raise HTTPException(status_code=404, detail="Task not found")

    return app


# CLI entry point
def main():
    """Main entry point for task runner"""
    import argparse

    parser = argparse.ArgumentParser(description="Sky Task Runner")
    parser.add_argument("--tick", type=int, default=30,
                       help="Tick interval in seconds (default: 30)")
    parser.add_argument("--api-port", type=int, default=None,
                       help="Start API server on port")
    args = parser.parse_args()

    if args.api_port:
        # Start API server
        try:
            import uvicorn
            app = create_task_api()
            if app:
                logger.info(f"Starting API server on port {args.api_port}")
                uvicorn.run(app, host="0.0.0.0", port=args.api_port)
            else:
                logger.error("Failed to create API app")
        except ImportError:
            logger.error("uvicorn not available - install with: pip install uvicorn")
    else:
        # Start scheduler loop
        queue = TaskQueue()
        scheduler = TaskScheduler(queue, tick_interval=args.tick)

        try:
            asyncio.run(scheduler.run())
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    main()
