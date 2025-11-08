"""
Sky Tool Registry - Auto-discovery and execution

Discovers tools from:
- tools/ (legacy location)
- src/agents/sky_tools/ (new structured location)
- Supports optional tool.json metadata files
"""
from pathlib import Path
import json
import subprocess
import sys
import shlex
from typing import List, Dict, Any, Optional

BASE = Path(__file__).resolve().parents[2]  # repo root

# Tool search paths
TOOL_PATHS = [
    BASE / "tools",
    BASE / "src" / "agents" / "sky_tools",
    BASE / "agents",  # legacy Phase 1 location
]

def _discover_tools() -> List[Dict[str, Any]]:
    """
    Auto-discover tools by scanning TOOL_PATHS for .py files
    Returns list of {name, path, description, args}
    """
    tools = []
    seen_names = set()

    for search_path in TOOL_PATHS:
        if not search_path.exists():
            continue

        for py_file in search_path.glob("**/*.py"):
            # Skip __init__, test files, and already-seen names
            if py_file.name.startswith("__") or py_file.name.startswith("test_"):
                continue

            tool_name = py_file.stem
            if tool_name in seen_names:
                continue

            seen_names.add(tool_name)

            # Check for optional metadata file
            metadata_file = py_file.with_suffix(".json")
            metadata = {}
            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            # Extract description from docstring if available
            description = metadata.get("description", "")
            if not description:
                try:
                    content = py_file.read_text(encoding="utf-8")
                    # Simple docstring extraction (first """...""" block)
                    if '"""' in content:
                        parts = content.split('"""', 2)
                        if len(parts) >= 2:
                            description = parts[1].strip().split("\n")[0]
                except Exception:
                    pass

            tools.append({
                "name": tool_name,
                "path": str(py_file),
                "description": description or f"Tool: {tool_name}",
                "args": metadata.get("args", []),
                "metadata": metadata
            })

    return sorted(tools, key=lambda t: t["name"])


def list_tools() -> List[Dict[str, Any]]:
    """
    Get list of all discovered tools
    Returns: [{name, path, description, args}, ...]
    """
    return _discover_tools()


def get_tool(name: str) -> Optional[Dict[str, Any]]:
    """
    Get tool metadata by name
    Returns: {name, path, description, args} or None
    """
    tools = _discover_tools()
    for tool in tools:
        if tool["name"] == name:
            return tool
    return None


def run_tool(name: str, args: List[str] = None) -> Dict[str, Any]:
    """
    Execute a tool by name

    Args:
        name: Tool name (e.g., "morning_reporter")
        args: List of command-line arguments

    Returns:
        {ok: bool, stdout: str, stderr: str, rc: int} or error dict
    """
    from .status import write_last_action

    tool = get_tool(name)

    if not tool:
        write_last_action("tool_not_found", {"name": name, "available": len(list_tools())})
        return {
            "ok": False,
            "error": f"Tool '{name}' not found",
            "available_tools": [t["name"] for t in list_tools()]
        }

    tool_path = Path(tool["path"])
    if not tool_path.exists():
        write_last_action("tool_path_missing", {"name": name, "path": str(tool_path)})
        return {
            "ok": False,
            "error": f"Tool path missing: {tool_path}"
        }

    # Build command
    cmd = f"{sys.executable} {shlex.quote(str(tool_path))}"
    if args:
        cmd += " " + " ".join(shlex.quote(str(a)) for a in args)

    # Execute
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            timeout=300  # 5 minute timeout
        )

        result = {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "rc": proc.returncode,
            "tool": name,
            "cmd": cmd
        }

        write_last_action(
            "tool_executed" if result["ok"] else "tool_failed",
            {"name": name, "rc": proc.returncode}
        )

        return result

    except subprocess.TimeoutExpired:
        write_last_action("tool_timeout", {"name": name})
        return {
            "ok": False,
            "error": f"Tool '{name}' timed out after 300s"
        }
    except Exception as e:
        write_last_action("tool_exception", {"name": name, "error": str(e)})
        return {
            "ok": False,
            "error": f"Tool execution failed: {e}"
        }


# Legacy compatibility - check if Phase 2 tool runner exists
def _get_legacy_runner():
    """Try to import legacy tool runner from Phase 2"""
    try:
        from agent.sky_tools_runner import run_tool as legacy_run
        return legacy_run
    except Exception:
        try:
            from src.agent.sky_tools_runner import run_tool as legacy_run
            return legacy_run
        except Exception:
            return None


# Expose unified interface
def execute_tool(name: str, args: List[str] = None) -> Dict[str, Any]:
    """
    Unified tool execution - tries new registry first, falls back to legacy
    """
    # Try new registry
    result = run_tool(name, args)

    # If tool not found, try legacy runner
    if not result.get("ok") and "not found" in result.get("error", ""):
        legacy = _get_legacy_runner()
        if legacy:
            return legacy(name, args)

    return result
