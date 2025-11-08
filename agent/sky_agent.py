import subprocess, sys, os
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
os.chdir(BASE)
subprocess.run([sys.executable, "agent/sky_api.py"])
