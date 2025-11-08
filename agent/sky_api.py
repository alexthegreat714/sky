from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import json
from pathlib import Path

APP = FastAPI(title="Sky API", version="0.1")
BASE = Path(__file__).resolve().parents[1]
CFG = BASE / "config" / "sky.yaml"
TOOLS = BASE / "agent" / "tool_registry.json"

class AskReq(BaseModel):
    prompt: str

@APP.get("/health")
def health():
    return {"status":"ok","service":"sky","port":7001}

@APP.get("/whoami")
def whoami():
    ident = (BASE / "agent" / "identity_sky.txt").read_text(encoding="utf-8")
    return {"identity": ident.splitlines()[:5]}

@APP.get("/tools")
def tools():
    data = json.loads(TOOLS.read_text(encoding="utf-8"))
    return data

@APP.post("/ask")
def ask(r: AskReq):
    # Placeholder: echo only. (Model/RAG wiring comes next.)
    return {"reply": f"(stub) Sky received: {r.prompt}"}

if __name__ == "__main__":
    uvicorn.run(APP, host="0.0.0.0", port=7001)
