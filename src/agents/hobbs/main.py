"""
Hobbs Agent (template)
- Own memory+RAG spaces
- Callable via senate bus later
- Phase 3 scaffold: no runtime yet
"""
from pathlib import Path

BASE = Path(__file__).resolve().parent
MEM_DIR = BASE / "memory"
RAG_DIR = BASE / "rag"
MEM_DIR.mkdir(exist_ok=True, parents=True)
RAG_DIR.mkdir(exist_ok=True, parents=True)

def describe():
    return {
        "name": "Hobbs",
        "role": "Farm & Physical Security",
        "memory_dir": str(MEM_DIR),
        "rag_dir": str(RAG_DIR),
    }
