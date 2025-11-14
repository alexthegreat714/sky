import importlib
import inspect
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class ToolRegistry:
    """Registry and awareness system for callable Sky modules."""

    REGISTRY_FILE = Path(r"C:\Users\blyth\Desktop\Engineering\rag_data\Sky\logs\tool_registry.json")

    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = Path(base_path or Path(__file__).resolve().parent)
        self.package = self.base_path.name
        self.tools: Dict[str, Dict[str, object]] = {}
        self.discover_tools()

    def _module_functions(self, module) -> List[str]:
        funcs = []
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if getattr(obj, "__module__", "") == module.__name__:
                funcs.append(name)
        return sorted(funcs)

    def discover_tools(self) -> None:
        """Scan the Sky directory for modules and record callable functions."""
        if not self.base_path.exists():
            return

        registry: Dict[str, Dict[str, object]] = {}
        for file_path in sorted(self.base_path.glob("*.py")):
            if file_path.name in {"app.py", "__init__.py"}:
                continue
            module_name = file_path.stem
            try:
                module = importlib.import_module(f"{self.package}.{module_name}")
                functions = self._module_functions(module)
                registry[module_name] = {"functions": functions, "loaded": True}
            except Exception as exc:  # pragma: no cover - logged for registry introspection
                registry[module_name] = {"error": str(exc), "loaded": False}

        self.tools = registry
        self._save()

    def _save(self) -> None:
        os.makedirs(self.REGISTRY_FILE.parent, exist_ok=True)
        payload = {"last_updated": datetime.now().isoformat(), "tools": self.tools}
        with open(self.REGISTRY_FILE, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def refresh(self) -> Dict[str, Dict[str, object]]:
        """Force a rescan and return the updated registry."""
        self.discover_tools()
        return self.tools

    def list_tools(self) -> Dict[str, Dict[str, object]]:
        """Return the most recent registry snapshot."""
        return self.tools

    def get_tool_info(self, name: str) -> Dict[str, object]:
        return self.tools.get(name, {})
