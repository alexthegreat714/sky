from pathlib import Path
import yaml, os

def load_config():
    candidates = [
        Path("config/sky.yaml"),
        Path("src/sky/config.yaml"),
    ]
    for p in candidates:
        if p.exists():
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {}

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)
