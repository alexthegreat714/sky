"""
Create a new agent package from template.
Example:
  python -m src.tools.create_agent --name apollo --role "Finance & Markets"
"""
from pathlib import Path
import argparse, shutil

TEMPLATE = {
    "dirs": ["memory", "rag"],
    "files": {
        "__init__.py": '"""{NAME}: scaffold package."""\n',
        "main.py": (
            '"""\n{NAME} Agent (template)\nRole: {ROLE}\n"""\n'
            "from pathlib import Path\n"
            "BASE = Path(__file__).resolve().parent\n"
            "def describe():\n"
            "    return {{'name':'{NAME}','role':'{ROLE}','base': str(BASE)}}\n"
        ),
        "rag/ingest.py": "def ingest(seed_dir: str):\n    print('{NAME} ingest scaffold —', seed_dir)\n",
    }
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--role", required=True)
    args = ap.parse_args()

    name = args.name.lower()
    base = Path(__file__).resolve().parents[1] / "agents" / name
    base.mkdir(parents=True, exist_ok=True)
    for d in TEMPLATE["dirs"]:
        (base / d).mkdir(exist_ok=True)
    for rel, content in TEMPLATE["files"].items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content.format(NAME=name.capitalize(), ROLE=args.role), encoding="utf-8")
    print(f"Created agent: {name} at {base}")

if __name__ == "__main__":
    main()
