from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from .status import read_status, write_last_action
from .orchestrator import get_orchestrator
from .tool_registry import run_tool, list_tools

app = FastAPI(title="Sky Service", version="0.2")

# Request models
class RunTaskRequest(BaseModel):
    task: str

class RunToolRequest(BaseModel):
    tool: str
    args: Optional[List[str]] = None

# Safe import of authority gate
def _safe_check_authority(action: str) -> bool:
    try:
        from src.governance.authority_gate import check_authority
        return check_authority(action)
    except Exception:
        # Default conservative: block risky actions
        restricted = {"restart_services", "modify_system_configs", "financial_transactions", "self_upgrade"}
        return action not in restricted

def _safe_refusal_message(action: str) -> str:
    try:
        from src.governance.authority_gate import refusal_message
        return refusal_message(action)
    except Exception:
        return f"Action '{action}' blocked by authority gate"

@app.get("/health")
def health():
    # ensure orchestrator is initialized
    get_orchestrator()
    return {"status": "ok", "component": "sky", "phase": "orchestrator-v1"}

@app.get("/status")
def status():
    return read_status()

@app.get("/tools")
def get_tools():
    """List all available tools"""
    tools = list_tools()
    return {
        "total": len(tools),
        "tools": [{"name": t["name"], "description": t["description"]} for t in tools]
    }

@app.post("/run_task")
def run_task(request: RunTaskRequest):
    """
    Execute a scheduled task by name
    Enforces authority checking before execution
    """
    orch = get_orchestrator()

    # Authority check: tasks require "run_approved_tools" permission
    if not _safe_check_authority("run_approved_tools"):
        msg = _safe_refusal_message("run_approved_tools")
        write_last_action("webhook_task_blocked", {"task": request.task, "reason": msg})
        raise HTTPException(status_code=403, detail=msg)

    # Execute task
    write_last_action("webhook_task_triggered", {"task": request.task})
    result = orch.handle_task(request.task)

    if not result.get("ok", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Task failed"))

    return result

@app.post("/run_tool")
def execute_tool_endpoint(request: RunToolRequest):
    """
    Execute a tool by name with optional arguments
    Enforces authority checking before execution
    """
    # Authority check: tools require "run_approved_tools" permission
    if not _safe_check_authority("run_approved_tools"):
        msg = _safe_refusal_message("run_approved_tools")
        write_last_action("webhook_tool_blocked", {"tool": request.tool, "reason": msg})
        raise HTTPException(status_code=403, detail=msg)

    # Execute tool
    write_last_action("webhook_tool_triggered", {"tool": request.tool, "args": request.args})
    result = run_tool(request.tool, args=request.args or [])

    if not result.get("ok", False):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", result.get("stderr", "Tool execution failed"))
        )

    return result

def run(host="0.0.0.0", port=7010):
    get_orchestrator()  # warm it up
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run()
