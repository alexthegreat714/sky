import argparse
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import requests
from playwright.async_api import async_playwright, Browser


# --- Configuration ---
DEFAULT_URLS = [
    "https://news.ycombinator.com/",
    "https://www.bbc.com/news",
    "https://www.reuters.com/",
    "https://arstechnica.com/",
    "https://www.theverge.com/",
]

# Local LLM endpoint (Open WebUI or similar)
DEFAULT_LLM_ENDPOINT = os.environ.get(
    "DAILY_AGENT_LLM_ENDPOINT",
    "http://127.0.0.1:3000/api/v1/chat",
)
DEFAULT_LLM_MODEL = os.environ.get("DAILY_AGENT_LLM_MODEL", "auto")

# Endpoint adapter type: 'openai', 'ollama_chat', 'ollama_generate'
EndpointType = str

# Paths
MEMORY_FILE = r"C:\Users\blyth\Desktop\Engineering\open-webui-full\backend\data\sky_memory\memory.txt"
LOG_FILE = os.path.join(os.path.dirname(__file__), "daily_info_log.txt")


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


async def extract_visible_content(browser: Browser, url: str, timeout_ms: int = 20000) -> Tuple[str, str]:
    """
    Navigate to the URL and extract:
    - title candidates (h1/h2)
    - a snippet of visible text from article/main/body
    Returns (titles_text, snippet_text)
    """
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/120.0.0.0 Safari/537.36"
        )
    )
    page = await context.new_page()
    page.set_default_timeout(timeout_ms)

    try:
        await page.goto(url, wait_until="domcontentloaded")

        # Try to accept simple cookie banners to reveal content
        for sel in [
            'button:has-text("Accept all")',
            'button:has-text("Accept")',
            'button:has-text("I agree")',
            'text=Accept all',
        ]:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click(timeout=1000)
            except Exception:
                pass

        # Extract title candidates and a visible snippet
        titles = await page.evaluate(
            """
            () => Array.from(document.querySelectorAll('h1, h2'))
                    .map(n => (n.innerText || '').trim())
                    .filter(Boolean)
                    .slice(0, 10)
            """
        )

        # Prefer <article> or <main>, else fallback to body
        snippet = await page.evaluate(
            """
            () => {
              const pick = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return '';
                const t = (el.innerText || '').replace(/\s+/g, ' ').trim();
                return t;
              };
              let t = pick('article');
              if (!t || t.length < 400) t = pick('main');
              if (!t || t.length < 400) t = (document.body?.innerText || '').replace(/\s+/g, ' ').trim();
              return t.substring(0, 5000); // cap to avoid huge payloads
            }
            """
        )

        titles_text = " | ".join(titles) if titles else ""
        snippet_text = snippet or ""
        return titles_text, snippet_text
    finally:
        await context.close()


def _post_openai_style(endpoint: str, model: str, system_prompt: str, user_prompt: str, timeout: int) -> str:
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENWEBUI_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 400,
        "stream": False,
    }
    resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        if data.get("choices"):
            ch0 = data["choices"][0]
            if isinstance(ch0, dict):
                msg = ch0.get("message") or {}
                if isinstance(msg, dict) and msg.get("content"):
                    return str(msg["content"]).strip()
                if ch0.get("text"):
                    return str(ch0["text"]).strip()
        if data.get("message") and isinstance(data["message"], dict) and data["message"].get("content"):
            return str(data["message"]["content"]).strip()
        if data.get("response"):
            return str(data["response"]).strip()
    return "(No structured response from LLM endpoint)"


def _post_ollama_chat(endpoint: str, model: str, user_prompt: str, timeout: int) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
    }
    resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        # Newer ollama chat
        if data.get("message") and isinstance(data["message"], dict) and data["message"].get("content"):
            return str(data["message"]["content"]).strip()
        # Some proxies return OpenAI-style
        if data.get("choices"):
            ch0 = data["choices"][0]
            if isinstance(ch0, dict):
                msg = ch0.get("message") or {}
                if isinstance(msg, dict) and msg.get("content"):
                    return str(msg["content"]).strip()
    return "(No structured response from Ollama chat)"


def _post_ollama_generate(endpoint: str, model: str, prompt: str, timeout: int) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
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
    """Probe a set of likely endpoints and return the first working one with its type."""
    candidates: list[tuple[str, EndpointType]] = []
    if preferred_endpoint:
        # Try to infer type by path
        etype: EndpointType = (
            "ollama_generate" if preferred_endpoint.endswith("/api/generate") else
            "ollama_chat" if preferred_endpoint.endswith("/api/chat") else
            "openai"
        )
        candidates.append((preferred_endpoint, etype))

    # Try OpenAI-style common paths
    candidates.extend([
        ("http://127.0.0.1:3000/v1/chat/completions", "openai"),
        ("http://127.0.0.1:8080/v1/chat/completions", "openai"),
    ])

    # Probe Ollama: chat and generate
    candidates.extend([
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
                _ = _post_openai_style(ep, test_model, "You are healthy.", "Say 'ok'", timeout)
                return ep, et, test_model
            if et == "ollama_chat":
                _ = _post_ollama_chat(ep, test_model, "Say 'ok'", timeout)
                return ep, et, test_model
            if et == "ollama_generate":
                _ = _post_ollama_generate(ep, test_model, "Say 'ok'", timeout)
                return ep, et, test_model
        except Exception:
            continue
    # Fallback to original default even if not working; summarizer will log failures
    return (preferred_endpoint or DEFAULT_LLM_ENDPOINT), "openai", model


def summarize_with_llm(
    raw_text: str,
    url: str,
    endpoint: str,
    model: str,
    endpoint_type: EndpointType,
    timeout: int = 20,
) -> str:
    """
    Send content to a local LLM endpoint and return a short summary.
    Tries to be compatible with common Chat Completions-style APIs.
    """
    system_prompt = (
        "You are a concise daily briefing assistant. "
        "Summarize key points in 3-6 bullets; highlight dates, names, numbers. "
        "If content is redundant or boilerplate, focus on unique updates."
    )
    user_prompt = (
        f"URL: {url}\n\n"
        f"Content (truncated):\n{raw_text[:5000]}\n\n"
        "Write a concise summary."
    )
    try:
        if endpoint_type == "openai":
            return _post_openai_style(endpoint, model, system_prompt, user_prompt, timeout)
        if endpoint_type == "ollama_chat":
            return _post_ollama_chat(endpoint, model, user_prompt, timeout)
        if endpoint_type == "ollama_generate":
            return _post_ollama_generate(endpoint, model, f"{system_prompt}\n\n{user_prompt}", timeout)
        return "(Unsupported endpoint type)"
    except Exception as e:
        logging.error("LLM summarization failed: %s", e)
        return "(Summarization failed; see log for details)"


def append_to_memory(url: str, summary: str) -> None:
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    block = f"[{ts_now()}] Summary from {url}:\n{summary}\n---\n"
    with open(MEMORY_FILE, "a", encoding="utf-8", newline="\n") as f:
        f.write(block)


async def process_url(browser: Browser, url: str, llm_endpoint: str, llm_model: str, endpoint_type: EndpointType) -> None:
    try:
        titles, snippet = await extract_visible_content(browser, url)
        if not snippet and not titles:
            logging.warning("No extractable content from %s", url)
        raw_data = f"Titles: {titles}\n\nSnippet: {snippet}"
        summary = summarize_with_llm(raw_data, url, endpoint=llm_endpoint, model=llm_model, endpoint_type=endpoint_type)
        append_to_memory(url, summary)
        logging.info("Processed and summarized: %s", url)
    except Exception as e:
        logging.exception("Failed processing %s: %s", url, e)


async def run_once(urls: List[str], llm_endpoint: str, llm_model: str, endpoint_type: EndpointType) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            for url in urls:
                await process_url(browser, url, llm_endpoint, llm_model, endpoint_type)
        finally:
            await browser.close()


def seconds_until_next_utc(hour: int = 9, minute: int = 0) -> int:
    now = datetime.now(timezone.utc)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return int((target - now).total_seconds())


async def run_daily(urls: List[str], llm_endpoint: str, llm_model: str, endpoint_type: EndpointType) -> None:
    while True:
        wait_s = seconds_until_next_utc(9, 0)
        logging.info("Sleeping %s seconds until next 09:00 UTC run", wait_s)
        await asyncio.sleep(wait_s)
        try:
            await run_once(urls, llm_endpoint, llm_model, endpoint_type)
            logging.info("Daily run completed")
        except Exception:
            logging.exception("Daily run encountered an error")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Daily Info Agent (Atlas-style)")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--test", action="store_true", help="Run once immediately (test mode)")
    mode.add_argument("--run", action="store_true", help="Run on a daily schedule (09:00 UTC)")
    p.add_argument(
        "--urls",
        nargs="*",
        default=DEFAULT_URLS,
        help="Override list of URLs to visit",
    )
    p.add_argument(
        "--endpoint",
        default=DEFAULT_LLM_ENDPOINT,
        help="LLM chat endpoint (default: %(default)s)",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_LLM_MODEL,
        help="LLM model name/alias (default: %(default)s)",
    )
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    logging.info("Starting Daily Info Agent | mode=%s | urls=%d", "test" if args.test else "run", len(args.urls))

    # Ensure memory directory exists early (avoid surprises later)
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)

    # Probe endpoint once and reuse
    resolved_endpoint, endpoint_type, resolved_model = probe_and_resolve_endpoint(args.endpoint, args.model, timeout=15)
    logging.info("Using LLM endpoint: %s (type=%s, model=%s)", resolved_endpoint, endpoint_type, resolved_model)

    try:
        if args.test:
            asyncio.run(run_once(args.urls, resolved_endpoint, resolved_model, endpoint_type))
        elif args.run:
            asyncio.run(run_daily(args.urls, resolved_endpoint, resolved_model, endpoint_type))
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
    except Exception:
        logging.exception("Fatal error in Daily Info Agent")


if __name__ == "__main__":
    main()
