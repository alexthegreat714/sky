"""
Sky/Hobbs log viewer scaffold.
Usage:
  python -m src.tools.log_viewer --file logs/sky_actions.jsonl --last 50 --grep memory
"""
from pathlib import Path
import argparse, json, re

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--last", type=int, default=50)
    p.add_argument("--grep", default=None)
    args = p.parse_args()

    path = Path(args.file)
    if not path.exists():
        print("No log file:", path)
        return

    lines = path.read_text(encoding="utf-8").splitlines()
    tail = lines[-args.last:]
    for line in tail:
        if args.grep and not re.search(args.grep, line, flags=re.I):
            continue
        try:
            obj = json.loads(line)
            print(f"{obj.get('ts')}: {obj.get('action')} :: {obj}")
        except Exception:
            print(line)

if __name__ == "__main__":
    main()
