import os, requests
from pathlib import Path
import json

BASE = Path(__file__).resolve().parents[1]

def _load_cfg():
    # Quick inline YAML loader to avoid PyYAML dependency initially
    # Will upgrade to yaml.safe_load once PyYAML added to requirements
    import yaml
    return yaml.safe_load((BASE / "config" / "sky.yaml").read_text(encoding="utf-8"))

_cfg = _load_cfg()
LLM = _cfg.get("llm", {})
LEG = _cfg.get("llm_legacy", {})

def chat(messages, system_prompt=None):
    mode = (LLM.get("mode") or "owui_openai").lower()
    if mode == "owui_openai":
        return _chat_openai(messages, system_prompt)
    elif mode == "owui_legacy":
        return _chat_legacy(messages, system_prompt)
    else:
        raise ValueError(f"Unsupported llm.mode: {mode}")

def _chat_openai(messages, system_prompt=None):
    # OpenAI-compatible via OWUI (/v1/chat/completions)
    base = LLM.get("base_url", "http://localhost:3000/v1").rstrip("/")
    url = f"{base}/chat/completions"
    api_key = LLM.get("api_key", "sk-local")
    model = LLM.get("model", "gemma-3-13b")
    temperature = float(LLM.get("temperature", 0.6))
    max_tokens = int(LLM.get("max_tokens", 512))

    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    msgs.extend(messages)

    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type":"application/json"},
        json={"model": model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]

def _chat_legacy(messages, system_prompt=None):
    # Older OWUI route: POST /api/chat {messages:[...]} -> {reply:"..."}
    base = LEG.get("base_url", "http://localhost:3000/api").rstrip("/")
    route = LEG.get("route", "/chat")
    url = f"{base}{route}"
    payload = {"messages": []}
    if system_prompt:
        payload["messages"].append({"role":"system","content":system_prompt})
    payload["messages"].extend(messages)
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json().get("reply","")
