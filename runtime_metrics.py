import time
from collections import deque
from typing import Deque

START_TS = time.time()
COUNTS = {"sky_chat": 0, "sky_write": 0, "sky_search": 0, "sky_review": 0, "sky_appendix": 0}
CHAT_LATENCIES: Deque[float] = deque(maxlen=200)
RAG_HITS: Deque[int] = deque(maxlen=200)
RAG_K: Deque[int] = deque(maxlen=200)
DEEPCODER_USAGE: Deque[int] = deque(maxlen=200)
CHAT_DEPTH_COUNTS = {"fast": 0, "normal": 0, "deep": 0}
GEMMA_CLASSIFIER_CALLS = 0


def record_event(name: str) -> None:
    key = f"sky_{name}"
    if key in COUNTS:
        COUNTS[key] += 1


def record_chat(
    latency_ms: float,
    rag_hit_count: int,
    deepcoder_used: bool,
    requested_k: int,
    depth: str,
    classifier_used: bool,
) -> None:
    COUNTS["sky_chat"] += 1
    CHAT_LATENCIES.append(latency_ms)
    RAG_HITS.append(rag_hit_count)
    RAG_K.append(requested_k)
    DEEPCODER_USAGE.append(1 if deepcoder_used else 0)
    if depth not in CHAT_DEPTH_COUNTS:
        depth = "normal"
    CHAT_DEPTH_COUNTS[depth] += 1
    global GEMMA_CLASSIFIER_CALLS
    if classifier_used:
        GEMMA_CLASSIFIER_CALLS += 1


def _percentile(samples, pct: float) -> float:
    if not samples:
        return 0.0
    sorted_vals = sorted(samples)
    index = int(round((pct / 100) * (len(sorted_vals) - 1)))
    return float(sorted_vals[index])


def snapshot() -> dict:
    uptime = time.time() - START_TS
    latencies = list(CHAT_LATENCIES)
    deep_usage = sum(DEEPCODER_USAGE) / len(DEEPCODER_USAGE) if DEEPCODER_USAGE else 0.0
    avg_hits = sum(RAG_HITS) / len(RAG_HITS) if RAG_HITS else 0.0
    k_val = RAG_K[-1] if RAG_K else 0
    return {
        "agent": "Sky",
        "sky_uptime_s": round(uptime, 2),
        "sky_counts": COUNTS.copy(),
        "sky_latency_ms": {
            "chat_p50": round(_percentile(latencies, 50), 2),
            "chat_p95": round(_percentile(latencies, 95), 2),
        },
        "sky_rag_hit_at_k": {"k": k_val, "avg_hits": round(avg_hits, 2)},
        "sky_deepcoder_usage_rate": round(deep_usage, 3),
        "sky_chat_depth_counts": CHAT_DEPTH_COUNTS.copy(),
        "sky_gemma_classifier_calls": GEMMA_CLASSIFIER_CALLS,
    }
