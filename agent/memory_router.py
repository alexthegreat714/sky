from pathlib import Path
import json, time

BASE = Path(__file__).resolve().parents[1]
MEM = BASE / "memory"
MEM.mkdir(exist_ok=True)
ST = MEM / "short_term.jsonl"
LT = MEM / "long_term.jsonl"

def write_short(summary: str, tags=None):
    rec = {"ts": time.time(), "type": "short", "summary": summary, "tags": tags or []}
    ST.write_text(ST.read_text(encoding="utf-8")+json.dumps(rec)+"\n", encoding="utf-8") if ST.exists() else ST.write_text(json.dumps(rec)+"\n", encoding="utf-8")

def write_long(summary: str, tags=None, importance=0.7):
    rec = {"ts": time.time(), "type": "long", "summary": summary, "tags": tags or [], "importance": importance}
    LT.write_text(LT.read_text(encoding="utf-8")+json.dumps(rec)+"\n", encoding="utf-8") if LT.exists() else LT.write_text(json.dumps(rec)+"\n", encoding="utf-8")
