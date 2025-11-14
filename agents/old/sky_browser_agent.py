import argparse
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

# browser-use (modern API) - use low-level session to avoid version-specific Agent API
try:
    from browser_use.browser import BrowserSession, BrowserProfile  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "browser-use is required. Install with: pip install browser-use playwright requests"
    ) from e


# =========================
# Configuration / Defaults
# =========================

# Where to store timestamped summaries
MEMORY_FILE = r"C:\Users\blyth\Desktop\Engineering\open-webui-full\backend\data\sky_memory\memory.txt"

# Log file co-located with this script
LOG_FILE = os.path.join(os.path.dirname(__file__), "browser_agent_log.txt")

# Local LLM endpoint used for summarization (Open WebUI API)
DEFAULT_SUMMARIZE_ENDPOINT = os.environ.get(
    "SKY_BROWSER_SUMMARIZE_ENDPOINT",
    "http://127.0.0.1:3000/api/v1/chat/completions",
)
# Model alias/name for summarization endpoint
DEFAULT_SUMMARIZE_MODEL = os.environ.get("SKY_BROWSER_SUMMARIZE_MODEL", "auto")

# Reasoning LLM settings (reserved for future direct integration)
DEFAULT_REASON_BASE_URL = os.environ.get("SKY_BROWSER_OPENAI_BASE_URL", "http://127.0.0.1:3000/api/v1")
DEFAULT_REASON_MODEL = os.environ.get("SKY_BROWSER_OPENAI_MODEL", "auto")
DEFAULT_REASON_API_KEY = os.environ.get("SKY_BROWSER_OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "not-needed"))

# Starter tasks (used when --task is omitted)
DEFAULT_TASKS = [
    "Find the newest hypersonics materials study published this week and summarize it.",
    "Check news for 'L3Harris hypersonic propulsion'.",
    "Search for emerging materials in thermal protection systems.",
]


# ==============
# Util / Logging
# ==============

def setup_logging() -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def ts_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def append_to_memory(summary_text: str) -> None:
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    block = f"[{ts_now()}] Browser Agent Summary: {summary_text}\n---\n"
    with open(MEMORY_FILE, "a", encoding="utf-8", newline="\n") as f:
        f.write(block)


EndpointType = str  # 'openai' | 'ollama_chat' | 'ollama_generate'


def _post_openai_style(endpoint: str, model: str, system_prompt: str, user_prompt: str, timeout: int) -> str:
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("OPENWEBUI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
        "stream": False,
    }
    r = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict):
        if data.get("choices"):
            ch0 = data["choices"][0]
            if isinstance(ch0, dict):
                if ch0.get("message") and isinstance(ch0["message"], dict):
                    c = ch0["message"].get("content")
                    if c:
                        return str(c).strip()
                if ch0.get("text"):
                    return str(ch0["text"]).strip()
        if data.get("message") and isinstance(data["message"], dict) and data["message"].get("content"):
            return str(data["message"]["content"]).strip()
        if data.get("response"):
            return str(data["response"]).strip()
    return "(No structured response from summarization endpoint)"


def _post_ollama_chat(endpoint: str, model: str, user_prompt: str, timeout: int) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": user_prompt}], "stream": False}
    r = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict):
        if data.get("message") and isinstance(data["message"], dict) and data["message"].get("content"):
            return str(data["message"]["content"]).strip()
        if data.get("choices"):
            ch0 = data["choices"][0]
            if isinstance(ch0, dict):
                msg = ch0.get("message") or {}
                if isinstance(msg, dict) and msg.get("content"):
                    return str(msg["content"]).strip()
    return "(No structured response from Ollama chat)"


def _post_ollama_generate(endpoint: str, model: str, prompt: str, timeout: int) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {"model": model, "prompt": prompt, "stream": False}
    r = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("response"):
        return str(data["response"]).strip()
    return "(No structured response from Ollama generate)"


def _ollama_first_model() -> Optional[str]:
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        r.raise_for_status()
        data = r.json()
        models = (data or {}).get("models") or []
        if models:
            name = models[0].get("name") or models[0].get("model")
            if name:
                return str(name)
    except Exception:
        return None
    return None


def probe_and_resolve_endpoint(preferred_endpoint: str | None, model: str, timeout: int = 5) -> tuple[str, EndpointType, str]:
    candidates: list[tuple[str, EndpointType]] = []
    if preferred_endpoint:
        et: EndpointType = (
            "ollama_generate" if preferred_endpoint.endswith("/api/generate") else
            "ollama_chat" if preferred_endpoint.endswith("/api/chat") else
            "openai"
        )
        candidates.append((preferred_endpoint, et))
    candidates.extend([
        ("http://127.0.0.1:3000/api/v1/chat/completions", "openai"),
        ("http://127.0.0.1:8080/api/v1/chat/completions", "openai"),
        ("http://127.0.0.1:11434/api/chat", "ollama_chat"),
        ("http://127.0.0.1:11434/api/generate", "ollama_generate"),
    ])
    for ep, et in candidates:
        try:
            test_model = model
            if et.startswith("ollama") and (not test_model or test_model == "auto"):
                m = _ollama_first_model()
                if m:
                    test_model = m
            if et == "openai":
                _ = _post_openai_style(ep, test_model or "auto", "health", "Say ok", timeout)
                return ep, et, test_model or "auto"
            if et == "ollama_chat":
                _ = _post_ollama_chat(ep, test_model or "llama3", "Say ok", timeout)
                return ep, et, test_model or "llama3"
            if et == "ollama_generate":
                _ = _post_ollama_generate(ep, test_model or "llama3", "Say ok", timeout)
                return ep, et, test_model or "llama3"
        except Exception:
            continue
    return (preferred_endpoint or DEFAULT_SUMMARIZE_ENDPOINT), "openai", model


def summarize(text: str, endpoint: str, model: str, endpoint_type: EndpointType, timeout: int = 30) -> str:
    system_prompt = (
        "You are a concise OS-level browsing agent for daily intel. "
        "Return a short, factual summary (3-8 bullets) focusing on names, dates, numbers, and key findings."
    )
    user_prompt = f"Content to summarize (may be truncated):\n{text[:6000]}"
    try:
        if endpoint_type == "openai":
            return _post_openai_style(endpoint, model, system_prompt, user_prompt, timeout)
        if endpoint_type == "ollama_chat":
            return _post_ollama_chat(endpoint, model, user_prompt, timeout)
        if endpoint_type == "ollama_generate":
            return _post_ollama_generate(endpoint, model, f"{system_prompt}\n\n{user_prompt}", timeout)
        return "(Unsupported endpoint type)"
    except Exception as e:
        logging.error("Summarization failed: %s", e)
        return "(Summarization failed; see log)"


def detect_blocked_or_captcha(text: str) -> Optional[str]:
    lowered = text.lower()
    indicators = [
        "captcha",
        "are you a robot",
        "unusual traffic",
        "access denied",
        "blocked",
        "forbidden",
    ]
    for key in indicators:
        if key in lowered:
            return key
    return None


async def run_agent_task(
    task: str,
    headless: bool = True,
    max_steps: Optional[int] = None,
    reason_base_url: str = DEFAULT_REASON_BASE_URL,
    reason_model: str = DEFAULT_REASON_MODEL,
    reason_api_key: str = DEFAULT_REASON_API_KEY,
    summarize_endpoint: str = DEFAULT_SUMMARIZE_ENDPOINT,
    summarize_model: str = DEFAULT_SUMMARIZE_MODEL,
    endpoint_type: EndpointType = "openai",
) -> str:
    """Simplified task runner using BrowserSession (API-stable) to navigate and extract text.

    - Performs a DuckDuckGo search for the task query
    - Captures a textual page state via browser-use DOM pipeline
    - Summarizes and appends to memory
    """
    try:
        profile = BrowserProfile(headless=headless, enable_default_extensions=False)
    except TypeError:
        # Some versions use different constructor; fall back to defaults
        profile = BrowserProfile()

    session = BrowserSession(browser_profile=profile)

    try:
        await session.start()

        import urllib.parse as _url
        query = _url.quote_plus(task)
        search_url = f"https://duckduckgo.com/?q={query}"

        await session.navigate_to(search_url, new_tab=False)

        # Let the page settle a bit if needed (the profile has own waits too)
        await asyncio.sleep(1.0)

        text_state = await session.get_state_as_text()
        if not text_state:
            text_state = "(No extractable text from page)"

        # Detect obvious blocks
        flag = detect_blocked_or_captcha(text_state)
        if flag:
            logging.warning("Potential access issue detected (%s) for task: %s", flag, task)

        # Summarize and persist
        raw_text = f"Task: {task}\n\n{text_state[:12000]}"  # cap size
        summary = summarize(raw_text, endpoint=summarize_endpoint, model=summarize_model, endpoint_type=endpoint_type)
        append_to_memory(summary)
        logging.info("Task completed and summary appended")
        return summary
    except Exception as e:
        logging.exception("Browser session failed for task '%s': %s", task, e)
        append_to_memory(f"Task: {task}\nResult: (Browser session failed: {e})")
        return "(Browser session failed)"
    finally:
        try:
            await session.stop()
        except Exception:
            pass


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sky Browser Agent (Atlas-style)")
    p.add_argument("--task", type=str, help="Task/query to execute (if omitted, run starter tasks)")
    p.add_argument("--headless", action="store_true", help="Run Chromium headless (default)")
    p.add_argument("--no-headless", dest="headless", action="store_false", help="Run Chromium with UI")
    p.set_defaults(headless=True)
    p.add_argument("--max-steps", type=int, default=None, help="Max agent steps/actions")

    # Reasoning LLM (used by browser-use)
    p.add_argument("--reason-base-url", default=DEFAULT_REASON_BASE_URL, help="OpenAI-compatible base URL for agent reasoning")
    p.add_argument("--reason-model", default=DEFAULT_REASON_MODEL, help="Reasoning model name")
    p.add_argument("--reason-api-key", default=DEFAULT_REASON_API_KEY, help="API key for reasoning model")

    # Summarization endpoint (Open WebUI)
    p.add_argument("--endpoint", default=DEFAULT_SUMMARIZE_ENDPOINT, help="Summarization endpoint (auto-probed if not working)")
    p.add_argument("--model", default=DEFAULT_SUMMARIZE_MODEL, help="Summarization model name")
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    logging.info("Sky Browser Agent starting | headless=%s | task_provided=%s", args.headless, bool(args.task))

    # Ensure memory directory exists early
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)

    # Probe endpoint
    resolved_endpoint, endpoint_type, resolved_model = probe_and_resolve_endpoint(args.endpoint, args.model, timeout=15)
    logging.info("Using summarization endpoint: %s (type=%s, model=%s)", resolved_endpoint, endpoint_type, resolved_model)

    try:
        if args.task:
            summary = asyncio.run(
                run_agent_task(
                    task=args.task,
                    headless=args.headless,
                    max_steps=args.max_steps,
                    reason_base_url=args.reason_base_url,
                    reason_model=args.reason_model,
                    reason_api_key=args.reason_api_key,
                    summarize_endpoint=resolved_endpoint,
                    summarize_model=resolved_model,
                    endpoint_type=endpoint_type,
                )
            )
            logging.info("Summary:\n%s", summary)
        else:
            # Run a short sequence of starter tasks
            for t in DEFAULT_TASKS:
                logging.info("Running starter task: %s", t)
                summary = asyncio.run(
                    run_agent_task(
                        task=t,
                        headless=args.headless,
                        max_steps=args.max_steps,
                        reason_base_url=args.reason_base_url,
                        reason_model=args.reason_model,
                        reason_api_key=args.reason_api_key,
                        summarize_endpoint=resolved_endpoint,
                        summarize_model=resolved_model,
                        endpoint_type=endpoint_type,
                    )
                )
                logging.info("Summary for task '%s':\n%s", t, summary)
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
    except Exception:
        logging.exception("Fatal error in Sky Browser Agent")


if __name__ == "__main__":
    main()
