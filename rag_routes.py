import logging
import os
import sys
from pathlib import Path

ROOT = r"C:\Users\blyth\Desktop\Engineering"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Blueprint, Response, current_app, jsonify, request, send_file

from common.rag_store import AgentRAG, read_jsonl_bomtolerant
from Sky.runtime_metrics import record_event

bp = Blueprint("sky_rag", __name__)
RAG = AgentRAG(agent_name="Sky")
BASELINE_FILE = Path(r"C:\Users\blyth\Desktop\Engineering\Sky\Sky.txt")


def seed_sky_baseline() -> dict:
    if not BASELINE_FILE.exists():
        return {"status": "missing", "path": str(BASELINE_FILE)}
    text = BASELINE_FILE.read_text(encoding="utf-8").strip()
    if not text:
        return {"status": "empty", "path": str(BASELINE_FILE)}
    RAG.remember(
        text=text,
        source="sky",
        kind="baseline",
        priority=0.05,
        tags=["sky", "baseline"],
    )
    return {"status": "seeded", "chars": len(text)}


@bp.route("/rag/write", methods=["POST"])
def rag_write():
    js = request.get_json() or {}
    text = (js.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "text required"}), 400
    priority = float(js.get("priority", 0.5))
    if priority < 0.8:
        meta = {k: v for k, v in js.items() if k != "text"}
        meta.setdefault("source", "api")
        meta.setdefault("kind", "note")
        meta["priority"] = priority
        RAG.write_short_term(text, meta)
        record_event("write")
        return jsonify({"ok": True, "short_term": True})
    doc_id = RAG.remember(
        text=text,
        source=js.get("source", "api"),
        kind=js.get("kind", "note"),
        priority=float(js.get("priority", 0.5)),
        tags=js.get("tags") or [],
        extra=js.get("extra") or {},
        id_=js.get("id"),
    )
    record_event("write")
    return jsonify({"ok": True, "id": doc_id})


@bp.route("/rag/seed_baseline", methods=["POST"])
def rag_seed_baseline_route():
    result = seed_sky_baseline()
    return jsonify(result)


@bp.route("/rag/shortterm/list", methods=["GET"])
def rag_shortterm_list():
    limit = int(request.args.get("limit", 100))
    since_raw = request.args.get("since_ts")
    since_ts = float(since_raw) if since_raw else None
    items = RAG.read_short_term(limit=limit, since_ts=since_ts)
    return jsonify({"items": items})


@bp.route("/rag/shortterm/export", methods=["GET"])
def rag_shortterm_export():
    path = RAG._short_term_path()
    if not os.path.exists(path):
        return Response("", mimetype="application/json")

    def generate():
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                yield line

    headers = {"Content-Disposition": 'attachment; filename="short_term.jsonl"'}
    return Response(generate(), mimetype="application/json", headers=headers)


@bp.route("/rag/appendix", methods=["POST"])
def rag_appendix():
    body = request.get_json(silent=True) or {}
    max_items = int(body.get("max_items", 50))
    summarize = bool(body.get("summarize", True))
    clear_after = bool(body.get("clear_after", True))
    result = RAG.appendix_promote(max_items=max_items, summarize=summarize)
    if clear_after and result.get("promoted", 0) > 0:
        result["short_term_cleared"] = RAG.clear_short_term()
    result["ok"] = True
    record_event("appendix")
    return jsonify(result)


@bp.route("/rag/search", methods=["POST"])
def rag_search():
    js = request.get_json() or {}
    q = (js.get("query") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "query required"}), 400
    res = RAG.search(
        query=q,
        top_k=int(js.get("top_k", 6)),
        min_priority=float(js.get("min_priority", 0.0)),
        since_ts=js.get("since_ts"),
        kinds=js.get("kinds"),
        tags_any=js.get("tags_any"),
    )
    record_event("search")
    return jsonify({"ok": True, "data": res})


@bp.route("/rag/review", methods=["POST"])
def rag_review():
    try:
        data = request.get_json(silent=True) or {}
        min_priority = 0.8
        top_k = int(data.get("top_k", 64))
        where_filter = data.get("where")

        candidates = RAG.search(
            query=data.get("query", "") or "",
            top_k=top_k,
            min_priority=min_priority,
            since_ts=None,
        ).get("results", [])

        if where_filter:

            def _match(meta: dict) -> bool:
                for key, value in where_filter.items():
                    if (meta or {}).get(key) != value:
                        return False
                return True

            candidates = [hit for hit in candidates if _match(hit.get("meta") or {})]

        existing = set(RAG.topic_signatures({"kind": "summary", "source": "review"}))
        created = []
        for hit in candidates:
            text = (hit.get("text") or "").strip()
            if not text:
                continue
            sig = RAG.signature_for_text(text)
            if sig in existing:
                continue
            summary = RAG.summarize_block(text)
            new_id = RAG.remember(
                text=summary,
                source="review",
                kind="summary",
                priority=0.95,
                tags=list({*(hit.get("meta") or {}).get("tags", []), "auto-review"}),
            )
            existing.add(sig)
            created.append(new_id)
        record_event("review")
        return jsonify({"ok": True, "created": created, "count": len(created)})
    except Exception as exc:
        current_app.logger.exception("rag_review failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/rag/import", methods=["POST"])
def rag_import():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"ok": False, "error": "file missing"}), 400
        imported = 0
        skipped = 0
        for raw in file.stream:
            try:
                rec = read_jsonl_bomtolerant(raw)
                text = (rec.get("text") or "").strip()
                if not text:
                    skipped += 1
                    continue
                meta = rec.get("meta") or {}
                source = meta.get("source", "import")
                kind = meta.get("kind", "note")
                priority_val = float(meta.get("priority", 0.5))
                tags = meta.get("tags") or []
                extra = meta.get("extra") or {}
                doc_id = rec.get("id")
                RAG.remember(
                    text=text,
                    source=source,
                    kind=kind,
                    priority=priority_val,
                    tags=tags,
                    extra=extra,
                    id_=doc_id,
                )
                imported += 1
            except Exception:
                current_app.logger.exception("rag_import item failed")
                skipped += 1
        return jsonify({"ok": True, "imported": imported, "skipped": skipped})
    except Exception as exc:
        current_app.logger.exception("rag_import failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/rag/list", methods=["GET"])
def rag_list():
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        ids = RAG.list_ids(limit=limit, offset=offset)
        return jsonify({"ids": ids, "limit": limit, "offset": offset})
    except Exception as exc:
        current_app.logger.exception("rag_list failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/rag/list", methods=["POST"])
def rag_list_post():
    try:
        body = request.get_json(silent=True) or {}
        where = body.get("where")
        if where == {}:
            where = None
        elif where is not None and not isinstance(where, dict):
            return jsonify({"ok": False, "error": "where must be an object"}), 400
        limit = max(1, min(int(body.get("limit", 50)), 200))
        offset = max(0, int(body.get("offset", 0)))
        result = RAG.get(
            ids=body.get("ids"),
            where=where,
            limit=limit,
            offset=offset,
        )
        return jsonify({"ok": True, **result})
    except Exception as exc:
        current_app.logger.exception("rag_list_post failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/rag/get", methods=["POST"])
def rag_get():
    try:
        body = request.get_json(force=True) or {}
        where = body.get("where")
        if where == {}:
            where = None
        result = RAG.get(
            ids=body.get("ids"),
            where=where,
            limit=int(body.get("limit", 100)),
            offset=int(body.get("offset", 0)),
        )
        return jsonify(result)
    except Exception as exc:
        current_app.logger.exception("rag_get failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/rag/delete", methods=["POST"])
def rag_delete():
    body = request.get_json(silent=True) or {}
    ids = body.get("ids")
    where = body.get("where")
    if where == {}:
        where = None
    if not ids and not where:
        return jsonify({"ok": False, "error": "Provide ids or a where filter"}), 400
    try:
        deleted = RAG.delete(ids=ids, where=where)
        return jsonify({"deleted": deleted, "ok": True})
    except Exception as exc:
        current_app.logger.exception("rag_delete failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/rag/update", methods=["POST"])
def rag_update():
    body = request.get_json(silent=True) or {}
    ids = body.get("ids")
    where = body.get("where")
    updates = {k: v for k, v in body.items() if k in ("priority", "tags", "source", "kind")}
    if not updates:
        return jsonify({"ok": False, "error": "No updatable fields provided"}), 400
    try:
        data = RAG.col.get(ids=ids) if ids else RAG.col.get(where=where)
        got_ids = data.get("ids", [])
        docs = data.get("documents", [])
        metas = data.get("metadatas", [])
        if not got_ids:
            return jsonify({"ok": True, "updated": 0})
        new_metas = []
        for m in metas:
            m = (m or {}).copy()
            for k, v in updates.items():
                m[k] = v
            if isinstance(m.get("tags"), list):
                m["tags"] = ",".join(str(t) for t in m["tags"])
            new_metas.append(m)
        RAG.col.delete(ids=got_ids)
        RAG.col.add(ids=got_ids, documents=docs, metadatas=new_metas)
        return jsonify({"ok": True, "updated": len(got_ids)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/rag/tags", methods=["GET"])
def rag_tags():
    data = RAG.col.get(include=["metadatas"])
    tags = set()
    for m in data.get("metadatas", []):
        if not m:
            continue
        val = m.get("tags")
        if isinstance(val, str):
            tags.update(t.strip() for t in val.split(",") if t.strip())
    return jsonify({"ok": True, "tags": sorted(tags)})
