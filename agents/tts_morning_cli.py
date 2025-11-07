import argparse
import datetime
import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import List


REPO_ROOT = Path(__file__).resolve().parents[2]
OWUI_DAILY = REPO_ROOT / "open-webui-full" / "backend" / "data" / "sky_daily"
TTS_SCRIPT = REPO_ROOT / "delayed-streams-modeling" / "scripts" / "tts_pytorch.py"
VOICE_REPO = REPO_ROOT / "delayed-streams-modeling" / "unmute" / "voices"
WORK_DIR = REPO_ROOT / "delayed-streams-modeling" / "unmute"
OUTPUT_DIR = WORK_DIR / "output"


def load_digest(date: str | None) -> dict:
    if date is None:
        date = datetime.date.today().isoformat()
    p = OWUI_DAILY / f"{date}.json"
    if not p.exists():
        raise FileNotFoundError(f"Daily digest not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def assemble_text(d: dict) -> List[str]:
    parts: List[str] = []
    parts.append("Good morning. Here is today's Sky digest.")
    if d.get("sleep_review"):
        parts.append("Sleep summary: " + d["sleep_review"]) 
    if d.get("overnight_news"):
        parts.append("Overnight news: " + "; ".join(d["overnight_news"]))
    if d.get("previous_day_news"):
        parts.append("Yesterday's news: " + "; ".join(d["previous_day_news"]))
    if d.get("plans_placeholder"):
        parts.append("Plans: " + "; ".join(d["plans_placeholder"]))
    if d.get("food_recommendations"):
        parts.append("Food: " + "; ".join(d["food_recommendations"]))
    if d.get("good_word_of_advice"):
        parts.append("Advice: " + d["good_word_of_advice"])

    # Chunk into manageable segments (~600-800 chars) to show progress
    chunks: List[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        while len(p) > 900:
            # split on last sentence end within first 900 chars
            cut = max(p.rfind(". ", 0, 900), p.rfind("; ", 0, 900), p.rfind(", ", 0, 900))
            if cut < 400:
                cut = 900
            chunk = p[:cut].strip()
            chunks.append(chunk)
            p = p[cut:].lstrip()
        chunks.append(p)
    return chunks


def concat_wavs(inputs: List[Path], dest: Path) -> None:
    if not inputs:
        raise ValueError("No WAVs to concatenate")
    with wave.open(str(inputs[0]), 'rb') as w0:
        params = w0.getparams()
        frames = [w0.readframes(w0.getnframes())]
    for path in inputs[1:]:
        with wave.open(str(path), 'rb') as wi:
            if wi.getparams() != params:
                raise ValueError(f"Incompatible WAV params for {path.name}")
            frames.append(wi.readframes(wi.getnframes()))
    with wave.open(str(dest), 'wb') as wo:
        wo.setparams(params)
        for fr in frames:
            wo.writeframes(fr)


def run_tts_chunk(text: str, out_path: Path, voice: str, device: str) -> int:
    # Ensure workdir exists for any relative resources
    env = os.environ.copy()
    env["TORCH_COMPILE_DISABLE"] = "1"
    cmd = [
        sys.executable,
        str(TTS_SCRIPT),
        "--voice-repo",
        str(VOICE_REPO),
        "--voice",
        voice,
        "-",
        str(out_path),
        "--device",
        device,
    ]
    proc = subprocess.run(cmd, input=text.encode("utf-8"), cwd=str(WORK_DIR), env=env)
    return proc.returncode


def print_progress(i: int, n: int, phase: str) -> None:
    width = 30
    filled = int((i / n) * width)
    bar = "#" * filled + "." * (width - filled)
    print(f"[{bar}] {i}/{n} {phase}", flush=True)


def main():
    ap = argparse.ArgumentParser(description="Sky Morning Digest → TTS (chunked)")
    ap.add_argument("--date", help="ISO date (YYYY-MM-DD). Defaults to today.")
    ap.add_argument("--voice", default="vctk/p225_023.wav", help="Voice relative to voice repo or absolute path")
    ap.add_argument("--device", default="cpu", help="torch device (cpu/cuda)")
    args = ap.parse_args()

    d = load_digest(args.date)
    date = d.get("date") or (args.date or datetime.date.today().isoformat())
    chunks = assemble_text(d)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    partials: List[Path] = []

    print(f"Sky TTS — Morning Digest for {date}")
    print(f"Voice repo: {VOICE_REPO}")
    print(f"Using voice: {args.voice}")
    print(f"Chunks: {len(chunks)}\n")

    n = len(chunks)
    start = time.time()
    for idx, chunk in enumerate(chunks, start=1):
        print_progress(idx - 1, n, "synth")
        out = OUTPUT_DIR / f"morning-{date}-part{idx:02d}.wav"
        rc = run_tts_chunk(chunk, out, args.voice, args.device)
        if rc != 0:
            print(f"Chunk {idx}/{n} failed (exit {rc}). Aborting.")
            sys.exit(rc)
        partials.append(out)
        print_progress(idx, n, "synth")

    print("\nConcatenating parts...")
    final = OUTPUT_DIR / f"morning-{date}.wav"
    try:
        concat_wavs(partials, final)
    except Exception as e:
        print(f"Concat failed: {e}")
        print("Parts left individually:")
        for p in partials:
            print(" -", p)
        sys.exit(0)

    dur = time.time() - start
    print(f"\nDone in {dur:.1f}s → {final}")


if __name__ == "__main__":
    main()

