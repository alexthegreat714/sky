from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn, json
from pathlib import Path
from . import sky_brain

APP = FastAPI(title="Sky API", version="0.2")
BASE = Path(__file__).resolve().parents[1]
TOOLS = BASE / "agent" / "tool_registry.json"

class AskReq(BaseModel):
    prompt: str

@APP.get("/health")
def health():
    return {"status":"ok","service":"sky","port":7001,"phase":2}

@APP.get("/whoami")
def whoami():
    ident = (BASE / "agent" / "identity_sky.txt").read_text(encoding="utf-8")
    return {"identity": ident.splitlines()[:5]}

@APP.get("/tools")
def tools():
    return json.loads(TOOLS.read_text(encoding="utf-8"))

@APP.post("/ask")
def ask(r: AskReq):
    return sky_brain.process(r.prompt)

if __name__ == "__main__":
    uvicorn.run(APP, host="0.0.0.0", port=7001)
