from pathlib import Path
from . import sky_llm
from . import memory_scoring
from . import sky_tools_runner
from . import logger

BASE = Path(__file__).resolve().parents[1]
IDENT = (BASE / "agent" / "identity_sky.txt").read_text(encoding="utf-8")

def process(prompt: str):
    # naive intent routing to get moving fast
    p = prompt.strip().lower()

    # tool intents
    if p.startswith("run tool "):
        parts = prompt.split()
        name = parts[2]
        args = parts[3:] if len(parts) > 3 else []
        out = sky_tools_runner.run_tool(name, args=args)
        return {"mode": "tool", "result": out}

    # memory write
    if p.startswith("remember ") or p.startswith("note "):
        content = prompt[len("remember "):] if p.startswith("remember ") else prompt[len("note "):]
        res = memory_scoring.decide_and_store(content, tags=["user_note"])
        logger.log("memory_store", {"content": content, **res})
        return {"mode":"memory","result":res}

    # default: answer via LLM (you can add RAG once wired)
    msgs = [{"role":"user","content": prompt}]
    reply = sky_llm.chat(messages=msgs, system_prompt=IDENT)
    logger.log("llm_reply", {"prompt": prompt, "chars": len(reply)})
    return {"mode":"llm","reply": reply}
