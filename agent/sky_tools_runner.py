import subprocess, sys, shlex, json
from pathlib import Path
from . import logger

BASE = Path(__file__).resolve().parents[1]
REG = json.loads((BASE / "agent" / "tool_registry.json").read_text(encoding="utf-8"))

def run_tool(name: str, args=None, dry_run=False):
    allowed = {t["name"]: t for t in REG.get("allowed_tools", [])}
    if name not in allowed:
        logger.log("tool_denied", {"tool": name})
        return {"ok": False, "error": "Tool not permitted for Sky."}

    tool = allowed[name]
    path = Path(tool["path"])
    if not path.exists():
        logger.log("tool_missing", {"tool": name, "path": str(path)})
        return {"ok": False, "error": f"Tool path missing: {path}"}

    cmd = f"{sys.executable} {shlex.quote(str(path))}"
    if args:
        cmd += " " + " ".join(shlex.quote(str(a)) for a in args)

    if dry_run:
        logger.log("tool_dry_run", {"tool": name, "cmd": cmd})
        return {"ok": True, "dry_run": True, "cmd": cmd}

    proc = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    result = {"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr, "rc": proc.returncode}
    logger.log("tool_exec", {"tool": name, "cmd": cmd, "rc": proc.returncode})
    return result
