import json
import logging
import os
import shutil
import subprocess
import sys
import time
import zipfile
import datetime
import datetime as _dt
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from flask import Blueprint, Flask, jsonify, render_template, request, send_file
from flask_cors import CORS

# ensure local imports work when running as a script
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

sys.path.append(str(Path(__file__).resolve().parents[1]))
ROOT = r"C:\Users\blyth\Desktop\Engineering"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from common.deepcoder import run as deepcoder_run
from common.dialogue_orchestrator import run_dialogue_test
from common.query_client import query_model
from common.rag_store import AgentRAG
from .garmin_agents_bridge import list_downloaded_files
from .garmin_pipeline import GARMIN_DATA_PATH, detect_new_files, run_garmin_pipeline
from .runtime_metrics import record_chat, snapshot as metrics_snapshot
from .tool_registry import ToolRegistry


def _load_env_file() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()

app = Flask(__name__, static_url_path="/static", static_folder="static", template_folder="templates")
CORS(app)
logging.basicConfig(level=logging.INFO)

_ABS_PATH = os.path.abspath(__file__)
_EXPECTED_PATH = r"C:\Users\blyth\Desktop\Engineering\Sky\app.py"
print(f"[Sky/app.py] Loaded from: {_ABS_PATH}")
if _ABS_PATH.replace("/", "\\") != _EXPECTED_PATH:
    raise SystemExit("[Sky/app.py] ABORT: path mismatch. Expected 'C:\\Users\\blyth\\Desktop\\Engineering\\Sky\\app.py'")

AGENT_NAME = "Sky"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")
OWUI_URL = os.getenv("OWUI_URL", "http://127.0.0.1:3000")
OWUI_MODEL = os.getenv("OWUI_MODEL", "")

SKY_RAG = AgentRAG("Sky")
TRACE_DIR = Path(SKY_RAG.get_collection_path()) / "traces"
TRACE_DIR.mkdir(parents=True, exist_ok=True)
TRACE_FILE = TRACE_DIR / "chat_traces.jsonl"
SNAPSHOT_GUARD_SECONDS = 5
LAST_ACTIVITY_TS = time.time()
registry = ToolRegistry()
SKY_BASELINE_PATH = r"C:\Users\blyth\Desktop\Engineering\Sky\Sky.txt"
BASELINE_MAX_CHARS = 1200
LAST_RUN_FILE = r"C:\Users\blyth\Desktop\Engineering\Sky\logs\morning_orchestrator\last.json"

try:
    from Sky import rag_routes as sky_rag_routes  # app folder now on sys.path
except Exception as e:
    print(f"[rag] import failed: {e!r}")
    traceback.print_exc()
else:
    try:
        app.register_blueprint(sky_rag_routes.bp)
        print("[rag] blueprint registered")
    except Exception as e:
        print(f"[rag] registration failed: {e}")


LOCAL_DEPTH_TAGS = {
    "deep": ["think longer", "consider deeply", "analyze this carefully", "reflect", "walk me through"],
    "fast": ["quick", "tl;dr", "short answer", "just tell me", "summary only"],
}
CODE_KEYWORDS = [
    "`",
    "stack trace",
    "traceback",
    "typeerror",
    "referenceerror",
    "def ",
    "class ",
    "select ",
    "insert ",
    "update ",
    "delete ",
    "error",
]
OPS_KEYWORDS = ["deploy", "rollback", "on-call", "incident", "slo", "page", "runbook", "playbook"]
PLANNING_KEYWORDS = ["plan", "roadmap", "milestone", "next step", "schedule"]
INTENT_VALUES = {"qa", "planning", "code", "ops_action", "unknown"}


def _dedupe(seq):
    seen = set()
    ordered = []
    for item in seq:
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def _load_baseline_context() -> str:
    try:
        with open(SKY_BASELINE_PATH, "r", encoding="utf-8") as handle:
            return handle.read(BASELINE_MAX_CHARS)
    except Exception:
        return ""


def _list_garmin_staged(n: int = 20) -> Dict[str, Any]:
    inbox = r"C:\Users\blyth\Desktop\Engineering\Sky\downloads\garmin"
    try:
        files = [fn for fn in os.listdir(inbox) if fn.lower().endswith(".csv")]
        files.sort(key=lambda fn: os.path.getmtime(os.path.join(inbox, fn)), reverse=True)
        latest = [{"file": fn, "mtime": os.path.getmtime(os.path.join(inbox, fn))} for fn in files[:n]]
        return {"inbox": inbox, "count": len(files), "latest": latest}
    except Exception as exc:
        return {"error": str(exc), "inbox": inbox}


def _resolve_iso_from_text(text: str) -> str:
    iso = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
    for token in text.split():
        token_clean = token.strip()
        if token_clean == "today":
            iso = _dt.date.today().isoformat()
        elif token_clean == "yesterday":
            iso = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
        elif len(token_clean) == 10 and token_clean[4] == "-" and token_clean[7] == "-":
            iso = token_clean
    return iso


def _record_last(date_iso: str, digest_path: str, exit_code: int) -> None:
    payload = {
        "date": date_iso,
        "digest_path": digest_path,
        "exit_code": exit_code,
        "timestamp": _dt.datetime.now().isoformat(),
    }
    os.makedirs(os.path.dirname(LAST_RUN_FILE), exist_ok=True)
    with open(LAST_RUN_FILE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _handle_garmin_command(message: str) -> Optional[Dict[str, Any]]:
    if not message:
        return None
    m = message.strip().lower()
    if not (m.startswith("/garmin") or ("garmin" in m and any(k in m for k in ("run", "status", "files", "full_run", "help")))):
        return None

    if "help" in m:
        return {
            "cmd": "garmin.help",
            "usage": "/garmin status | /garmin files | /garmin run [today|yesterday|YYYY-MM-DD]",
        }

    iso = _resolve_iso_from_text(m)

    if "status" in m and "run" not in m and "files" not in m:
        digest = rf"C:\Users\blyth\Desktop\Engineering\open-webui-full\backend\data\sky_daily\{iso}.json"
        return {
            "cmd": "garmin.status",
            "date": iso,
            "digest_exists": os.path.exists(digest),
            "digest_path": digest,
            "staged": _list_garmin_staged(),
        }

    if "files" in m:
        return {"cmd": "garmin.files", "date": iso, "staged": _list_garmin_staged()}

    if "run" in m or "full_run" in m:
        bat = r"C:\Users\blyth\Desktop\Engineering\Sky\tools\garmin_full_morning.bat"
        env = os.environ.copy()
        env["PYTHONPATH"] = r"C:\Users\blyth\Desktop\Engineering"
        try:
            rc = subprocess.call([bat, iso], env=env, creationflags=0x08000000)
        except Exception as exc:
            return {"cmd": "garmin.run", "date": iso, "status": "error", "error": str(exc)}
        digest = rf"C:\Users\blyth\Desktop\Engineering\open-webui-full\backend\data\sky_daily\{iso}.json"
        _record_last(iso, digest, rc)
        return {
            "cmd": "garmin.run",
            "date": iso,
            "exit_code": rc,
            "digest_exists": os.path.exists(digest),
            "digest_path": digest,
        }

    return {
        "cmd": "garmin.help",
        "usage": "/garmin status | /garmin files | /garmin run [today|yesterday|YYYY-MM-DD]",
    }


def _handle_morning_command(message: str) -> Optional[Dict[str, Any]]:
    if not message:
        return None
    m = message.strip().lower()
    if not m.startswith("/morning"):
        return None
    iso = _resolve_iso_from_text(m)
    digest = rf"C:\Users\blyth\Desktop\Engineering\open-webui-full\backend\data\sky_daily\{iso}.json"
    if "path" in m:
        return {"cmd": "morning.path", "date": iso, "digest_path": digest, "exists": os.path.exists(digest)}
    if "show" in m:
        if not os.path.exists(digest):
            return {"cmd": "morning.show", "date": iso, "exists": False}
        try:
            with open(digest, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            slim = {
                "date": iso,
                "sleep_review": data.get("sleep_review"),
                "good_word_of_advice": data.get("good_word_of_advice"),
            }
            return {"cmd": "morning.show", "exists": True, "data": slim}
        except Exception as exc:
            return {"cmd": "morning.show", "error": repr(exc)}
    return {"cmd": "morning.help", "usage": "/morning show [date] | /morning path [date]"}


NLU_RUN_PATTERNS = [
    re.compile(r"\b(run|do|start|kick ?off|begin|trigger)\b.*\b(morning|garmin)\b", re.I),
    re.compile(r"\b(morning)\b.*\b(report|digest|sweep)\b", re.I),
]


def _handle_nlu_morning(message: str) -> Optional[Dict[str, Any]]:
    """
    Natural-language trigger for the morning sweep.
    Always returns a structured dict; never raises.
    """
    try:
        m = (message or "").strip()
        if not m:
            return None
        if not any(pattern.search(m) for pattern in NLU_RUN_PATTERNS):
            return None

        iso = _resolve_iso_from_text(m.lower())
        low = m.lower()
        if "today" in low:
            iso = _dt.date.today().isoformat()
        elif "yesterday" in low:
            iso = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
        else:
            for token in re.findall(r"\d{4}-\d{2}-\d{2}", m):
                iso = token
                break

        bat = r"C:\Users\blyth\Desktop\Engineering\Sky\tools\garmin_full_morning.bat"
        digest = rf"C:\Users\blyth\Desktop\Engineering\open-webui-full\backend\data\sky_daily\{iso}.json"
        env = os.environ.copy()
        env["PYTHONPATH"] = r"C:\Users\blyth\Desktop\Engineering"
        try:
            rc = subprocess.call([bat, iso], env=env, creationflags=0x08000000)
            resp: Dict[str, Any] = {
                "intent": "morning.run",
                "ok": rc == 0,
                "date": iso,
                "exit_code": rc,
                "digest_exists": os.path.exists(digest),
                "digest_path": digest,
            }
            _record_last(iso, digest, rc)
            if rc == 42:
                resp["status"] = "cooldown"
                resp["hint"] = "Cloudflare 1015 detected; try again later or refresh manually."
            if rc not in (0, 42):
                resp["error"] = f"runner exited with code {rc}"
            return resp
        except Exception as exc:
            return {
                "intent": "morning.run",
                "ok": False,
                "date": iso,
                "error": f"subprocess failed: {exc!r}",
                "digest_path": digest,
            }
    except Exception as exc:
        return {"intent": "morning.run", "ok": False, "error": f"nlu handler error: {exc!r}"}


def detect_local_tags(msg: str) -> dict:
    text = msg.lower()
    tags = []
    depth = "normal"
    for phrase in LOCAL_DEPTH_TAGS["deep"]:
        if phrase in text:
            depth = "deep"
            tags.append(phrase)
    for phrase in LOCAL_DEPTH_TAGS["fast"]:
        if phrase in text and depth != "deep":
            depth = "fast"
            tags.append(phrase)

    intent = "unknown"
    for keyword in CODE_KEYWORDS:
        if keyword in text:
            intent = "code"
            tags.append(keyword)
            break
    if intent == "unknown":
        for keyword in OPS_KEYWORDS:
            if keyword in text:
                intent = "ops_action"
                tags.append(keyword)
                break
    if intent == "unknown":
        for keyword in PLANNING_KEYWORDS:
            if keyword in text:
                intent = "planning"
                tags.append(keyword)
                break
    if intent == "unknown" and "?" in msg:
        intent = "qa"
        tags.append("?")
    return {"intent": intent, "depth": depth, "tags": _dedupe(tags)}


def _parse_classifier_json(raw: str) -> dict:
    if not isinstance(raw, str):
        return {}
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    snippet = raw[start : end + 1]
    try:
        data = json.loads(snippet)
    except json.JSONDecodeError:
        return {}
    intent = (data.get("intent") or "").lower()
    if intent not in INTENT_VALUES:
        intent = "unknown"
    data["intent"] = intent
    data["needs_deepcoder"] = bool(data.get("needs_deepcoder"))
    data["needs_long_reflection"] = bool(data.get("needs_long_reflection"))
    return data


def run_gemma_classifier(message: str) -> dict:
    prompt = (
        "You are the classifier. Return a JSON object like:\n"
        '{"intent": "qa|planning|code|ops_action|unknown",\n'
        ' "needs_deepcoder": true|false,\n'
        ' "needs_long_reflection": true|false}\n\n'
        f"Message:\n{message}\n"
    )
    try:
        raw = query_model(prompt)
    except Exception as exc:
        logging.warning("Sky classifier call failed: %s: %s", type(exc).__name__, exc)
        return {}
    return _parse_classifier_json(raw)


def gather_hits(intent: str, message: str, depth: str):
    if intent == "planning":
        base_top = 8
        search_top = 12
        kinds = ["summary"]
    elif intent == "code":
        base_top = 6
        search_top = 10
        kinds = ["code", "summary"]
    elif intent == "ops_action":
        base_top = 8
        search_top = 12
        kinds = None
    else:
        base_top = 6
        search_top = 6
        kinds = None

    if depth == "fast":
        top_k = 3
        search_top = max(search_top, 5)
    elif depth == "deep":
        top_k = max(8, base_top)
        search_top = max(search_top, top_k + 2)
    else:
        top_k = base_top

    res = SKY_RAG.search(query=message, top_k=search_top, kinds=kinds)
    hits = res.get("results", [])
    if intent == "ops_action":
        hits = [
            h
            for h in hits
            if (h.get("meta") or {}).get("source") == "ops" and (h.get("meta") or {}).get("kind") == "summary"
        ]
    else:
        hits = [
            h
            for h in hits
            if (h.get("meta") or {}).get("kind") != "schedule"
        ]
    return hits[:top_k], top_k


def log_trace(
    intent: str,
    depth: str,
    message: str,
    rag_hits: int,
    deep_used: bool,
    latency_ms: float,
    chain: str,
    local_tags: list,
    gemma_classifier_used: bool,
    gemma_classifier_output: dict,
) -> None:
    record = {
        "ts": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        "intent": intent,
        "depth": depth,
        "local_tags": local_tags,
        "gemma_classifier_used": gemma_classifier_used,
        "gemma_classifier_output": gemma_classifier_output,
        "message": message,
        "rag_hits": rag_hits,
        "deepcoder_used": deep_used,
        "latency_ms": round(latency_ms, 2),
        "chain": chain,
    }
    with open(TRACE_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _can_snapshot() -> bool:
    return (time.time() - LAST_ACTIVITY_TS) >= SNAPSHOT_GUARD_SECONDS


@app.before_request
def _track_activity():
    global LAST_ACTIVITY_TS
    if request.endpoint not in {"rag_snapshot", "rag_restore"}:
        LAST_ACTIVITY_TS = time.time()


@app.route("/")
def home():
    return render_template("index.html", agent=AGENT_NAME)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "ts": datetime.utcnow().isoformat() + "Z"})


@app.route("/meta")
def meta():
    ollama_ok, ollama_version = False, None
    try:
        r = requests.get(f"{OLLAMA_URL}/api/version", timeout=2)
        if r.ok:
            ollama_ok = True
            ollama_version = r.json().get("version")
    except Exception:
        pass

    return jsonify(
        {
            "agent": AGENT_NAME,
            "provider": LLM_PROVIDER,
            "ollama": {"url": OLLAMA_URL, "model": OLLAMA_MODEL, "up": ollama_ok, "version": ollama_version},
            "owui": {"url": OWUI_URL, "model": OWUI_MODEL},
        }
    )


@app.route("/chat", methods=["POST"])
def chat():
    start = time.perf_counter()
    data = request.get_json(force=True) or {}
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"reasoning": "(none)", "reply": "Say something first."})

    override = _handle_garmin_command(user_msg)
    if override is not None:
        return jsonify(override), 200

    morning_override = _handle_morning_command(user_msg)
    if morning_override is not None:
        return jsonify(morning_override), 200

    nlu_override = _handle_nlu_morning(user_msg)
    if nlu_override is not None:
        return jsonify(nlu_override), 200

    local_scan = detect_local_tags(user_msg)
    local_tags = local_scan.get("tags", [])
    intent = local_scan.get("intent") if local_scan else "unknown"
    if intent not in INTENT_VALUES:
        intent = "unknown"
    depth = local_scan.get("depth") if local_scan else "normal"
    if depth not in {"fast", "normal", "deep"}:
        depth = "normal"

    gemma_classifier_used = True
    gemma_output = run_gemma_classifier(user_msg)
    if gemma_output and intent == "unknown":
        new_intent = gemma_output.get("intent", intent)
        if new_intent in INTENT_VALUES:
            intent = new_intent
    if gemma_output and gemma_output.get("needs_long_reflection"):
        depth = "deep"
    if gemma_output and gemma_output.get("needs_deepcoder") and intent not in ("code", "ops_action"):
        intent = "code"

    hits, requested_k = gather_hits(intent, user_msg, depth)
    rag_preamble = ""
    if hits:
        rag_preamble = "\n".join(hit.get("text", "") for hit in hits if hit.get("text"))
    else:
        rag_preamble = _load_baseline_context()
    ctx_lines = [rag_preamble] if rag_preamble else []
    tool_block = ""
    deep_used = False
    allow_deepcoder = depth != "fast" and (depth == "deep" or intent in ("code", "ops_action"))
    if allow_deepcoder:
        tool_block = deepcoder_run(user_msg, intent, hits)
        deep_used = bool(tool_block)

    blocks = []
    if ctx_lines:
        blocks.append("Context:\n" + "\n".join(ctx_lines))
    if tool_block:
        blocks.append("[DeepCoder]\n" + tool_block)
    if depth == "fast":
        instruction = (
            "Instruction: Provide a concise answer (1-2 sentences). Use context only if essential."
            " If uncertain, say what's missing.\nUser: "
        )
    elif depth == "deep":
        instruction = (
            "Instruction: Think step-by-step before responding. Reference context/tool insights and mention unknowns."
            "\nUser: "
        )
    else:
        instruction = (
            "Instruction: Answer briefly (3-6 sentences). Use the context/tool block if it helps."
            " If uncertain, say what's missing.\nUser: "
        )
    blocks.append(instruction + user_msg)
    prompt = "\n\n".join(blocks)
    reply = query_model(prompt)

    latency_ms = (time.perf_counter() - start) * 1000.0
    record_chat(latency_ms, len(hits), deep_used, requested_k, depth, gemma_classifier_used)
    chain = f"{intent}:{depth}" + ("->deepcoder" if deep_used else "") + "->gemma"
    log_trace(
        intent,
        depth,
        user_msg,
        len(hits),
        deep_used,
        latency_ms,
        chain,
        local_tags,
        gemma_classifier_used,
        gemma_output or {},
    )

    reasoning = "\n".join(blocks[:-1]) if blocks[:-1] else "(none)"
    return jsonify({"reasoning": reasoning, "reply": reply, "intent": intent, "depth": depth})


@app.route("/metrics")
def metrics():
    return jsonify(metrics_snapshot())


@app.route("/dialogue/test", methods=["GET", "POST"])
def dialogue_test():
    body = request.get_json(silent=True) or {}
    turns = body.get("turns") or request.args.get("turns", type=int) or 5
    result = run_dialogue_test(int(turns))
    return jsonify(result), 200


@app.route("/tools", methods=["GET"])
def list_tools():
    registry.refresh()
    payload = {"registry_file": str(ToolRegistry.REGISTRY_FILE), "tools": registry.list_tools()}
    return jsonify(payload), 200


@app.route("/garmin/run", methods=["POST"])
def garmin_run():
    result = run_garmin_pipeline()
    return jsonify(result), 200


@app.route("/garmin/status", methods=["GET"])
def garmin_status():
    GARMIN_DATA_PATH.mkdir(parents=True, exist_ok=True)
    files = sorted(os.listdir(GARMIN_DATA_PATH))
    pending = detect_new_files()
    return jsonify({
        "files": files,
        "pending_new": pending,
        "data_path": str(GARMIN_DATA_PATH),
        "downloaded_files": list_downloaded_files(),
    }), 200


@app.route("/garmin/full_run", methods=["POST"])
def garmin_full_run():
    body = request.get_json(silent=True) or {}
    ensure = body.get("ensure_download", True)
    result = run_garmin_pipeline(ensure_download=bool(ensure))
    result["ensure_download"] = bool(ensure)
    return jsonify(result), 200


@app.route("/garmin/files", methods=["GET"])
def garmin_files():
    GARMIN_DATA_PATH.mkdir(parents=True, exist_ok=True)
    return jsonify({"files": list_downloaded_files(), "data_path": str(GARMIN_DATA_PATH)}), 200


ops_bp = Blueprint("sky_ops", __name__)


@ops_bp.route("/ops/last", methods=["GET"])
def ops_last():
    if not os.path.exists(LAST_RUN_FILE):
        return jsonify({"status": "none"}), 404
    with open(LAST_RUN_FILE, "r", encoding="utf-8") as handle:
        return jsonify(json.load(handle))


app.register_blueprint(ops_bp)


@app.route("/rag/snapshot", methods=["GET"])
def rag_snapshot():
    if not _can_snapshot():
        return jsonify({"error": "Recent activity detected. Pause traffic before snapshot."}), 409
    base_path = Path(SKY_RAG.get_collection_path())
    snap_dir = base_path / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    snapshot_path = snap_dir / f"sky_snapshot_{timestamp}.zip"
    with zipfile.ZipFile(snapshot_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(base_path):
            for file in files:
                full_path = Path(root) / file
                arcname = full_path.relative_to(base_path)
                zf.write(full_path, arcname)
    return send_file(str(snapshot_path), as_attachment=True, download_name=snapshot_path.name)


@app.route("/rag/restore", methods=["POST"])
def rag_restore():
    global SKY_RAG, TRACE_DIR, TRACE_FILE
    if not _can_snapshot():
        return jsonify({"error": "Recent activity detected. Pause traffic before restore."}), 409
    body = request.get_json(force=True) or {}
    path = body.get("path")
    if not path or not os.path.exists(path):
        return jsonify({"error": "Snapshot path invalid"}), 400

    try:
        sky_rag_routes.RAG.client.delete_collection(sky_rag_routes.RAG.col.name)
    except Exception:
        pass

    base_path = Path(SKY_RAG.get_collection_path())
    shutil.rmtree(base_path, ignore_errors=True)
    os.makedirs(base_path, exist_ok=True)
    with zipfile.ZipFile(path, "r") as zf:
        zf.extractall(base_path)

    SKY_RAG = AgentRAG("Sky")
    sky_rag_routes.RAG = AgentRAG("Sky")
    TRACE_DIR = Path(SKY_RAG.get_collection_path()) / "traces"
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    TRACE_FILE = TRACE_DIR / "chat_traces.jsonl"
    return jsonify({"ok": True, "restored": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5011, debug=False, threaded=True)

