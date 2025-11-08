"""
Runner convenience (no install needed):
  python -m src.tools.run_sky --mode loop --seconds 60
  python -m src.tools.run_sky --mode service --port 7010
"""
import argparse
from src.sky.orchestrator import SkyOrchestrator
from src.sky.service import run as run_service

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["loop","service"], default="loop")
    ap.add_argument("--seconds", type=int, default=None, help="loop mode: stop after N seconds")
    ap.add_argument("--port", type=int, default=7010, help="service mode port")
    args = ap.parse_args()

    if args.mode == "loop":
        SkyOrchestrator().loop(stop_after_seconds=args.seconds)
    else:
        run_service(port=args.port)

if __name__ == "__main__":
    main()
