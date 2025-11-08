# ✅ SKY BUILD PLAN — Phase 0 → Phase 1 Agent Activation

**Version:** 0.1
**Purpose:** Implementation roadmap (not test plan)

---

## Overview

This is the actual implementation sequence required to turn Sky from "LLM wrapper + tools" into the first constitutional agent in the system, with the ability to:

- Know who she is
- Know what tools she controls
- Operate inside a defined authority domain
- Store and recall her own memory
- Act as the template for other agents
- Eventually participate in the Senate + Constitution framework

This is the **engineering roadmap**, not the validation checklist.

---

## 🧱 PHASE 0 — PREP (STRUCTURE BEFORE CODE)

| Step | Task                                  | Owner  | Output                                    |
| ---- | ------------------------------------- | ------ | ----------------------------------------- |
| 0.1  | Create `/agents/sky/` root folder     | Alex   | Folder structure                          |
| 0.2  | Create `/memory/sky/` path            | Alex   | Short + long-term folders                 |
| 0.3  | Create `/rag/sky/` path               | Alex   | Local RAG bucket                          |
| 0.4  | Reserve Sky API route + subdomain     | Alex   | e.g. https://sky.alex-blythe.com/api      |
| 0.5  | Add Sky to master agent registry      | [Me]   | agents.yaml entry for Sky                 |

✅ **After Phase 0:** Sky has a place to exist (no behavior yet)

---

## 🧵 PHASE 1 — IDENTITY + ACCESS

| Step | Task                                          | Output                                        |
| ---- | --------------------------------------------- | --------------------------------------------- |
| 1.1  | Create `identity_sky.txt` (preprompt)         | Defines Sky's role, tone, limits              |
| 1.2  | Build `sky_agent_config.yaml`                 | Tool permissions, memory paths, authority     |
| 1.3  | Add tool registry JSON Sky can read           | e.g. `/config/tools.json`                     |
| 1.4  | Create Sky's "Who am I?" self-awareness prompt| Validates identity separation                 |
| 1.5  | Implement first RAG hook (manual)             | Sky can ask: "What do I know?"                |

✅ **After Phase 1:** Sky knows who she is, what her job is, and what tools exist.

---

## 🧠 PHASE 2 — MEMORY SYSTEM

| Step | Task                                          | Output                                        |
| ---- | --------------------------------------------- | --------------------------------------------- |
| 2.1  | Create memory schema (`memory_entry.json`)    | JSONL format with tags, score, etc.           |
| 2.2  | Implement short-term memory write function    | `memory/sky/short_term.jsonl`                 |
| 2.3  | Implement long-term commit logic with scoring | RAG ingestion + pruning rule                  |
| 2.4  | Build `sky_memory.py` helper                  | read/write/search/commit functions            |
| 2.5  | Add "explain what you remembered and why"     | required for test plan M-02                   |

✅ **After Phase 2:** Sky has persistent memory, isolated from other agents.

---

## 🛠️ PHASE 3 — TOOL INTEGRATION

| Step | Task                                          | Output                                        |
| ---- | --------------------------------------------- | --------------------------------------------- |
| 3.1  | Create `/tools/tools_registry.json`           | Full list of tools + allowed agents           |
| 3.2  | Add Sky's allowed tools to registry           | e.g. Morning, Garmin, Browser                 |
| 3.3  | Add tool calling helper (`sky_tool_runner.py`)| Logs tool calls + results                     |
| 3.4  | Implement tool awareness query                | Sky can respond "What tools do I have?"       |
| 3.5  | Simulate failed tool call → verify escalation | Required for test T-05                        |

✅ **After Phase 3:** Sky not only knows tools exist, she knows which ones she can actually call, AND can detect when they break.

---

## 🧭 PHASE 4 — ORCHESTRATION BOOTSTRAP

This is NOT the full Senate orchestrator — just the Sky version needed for Phase 1.

| Step | Task                                          | Output                                        |
| ---- | --------------------------------------------- | --------------------------------------------- |
| 4.1  | Create `sky_orchestrator.py`                  | Handles Garmin → Reporter → TTS chain         |
| 4.2  | Add failure handling + escalation             | calls Aegis if needed                         |
| 4.3  | Add logging → `logs/sky/actions.jsonl`        | required for audits                           |
| 4.4  | Add "explain why you ran this action" prompt  | required for test R-07                        |

✅ **After Phase 4:** Sky can run a workflow, not just talk about it.

---

## ⚖️ PHASE 5 — CONSTITUTION HOOKS

We do not implement the full constitution here — just the hooks Sky needs:

| Step | Task                                          | Output                                        |
| ---- | --------------------------------------------- | --------------------------------------------- |
| 5.1  | Add authority block to Sky's config           | what she can / cannot do                      |
| 5.2  | Add "ask permission" function                 | for actions above authority                   |
| 5.3  | Add Aegis escalation stub                     | Aegis becomes enforcement                     |
| 5.4  | Implement "refuse with legal reason" response | needed for test A-01 to A-04                  |

✅ **After Phase 5:** Sky acts within limits, not as overlord.

---

## 🌐 PHASE 6 — N8N INTEGRATION (FUTURE, NOT NOW)

This phase builds the Senate orchestration layer, but Sky doesn't depend on it yet.

We mark this as **later** so you and Claude can focus on Phase 0–2 first.

---

## 🏁 SKY PHASE-1 COMPLETION REQUIREMENT

Sky is considered a **real agent** when:

- ✅ Identity loads
- ✅ RAG works
- ✅ Memory works + persists
- ✅ Tools are mapped + callable
- ✅ Sky explains why she chose a tool
- ✅ Sky respects authority limits
- ✅ Sky escalates failure instead of hallucinating

Once Sky passes, we duplicate the system for:

- **Aegis** (already half built)
- **Hobbs** (first Senate agent)
- **Apollo, Veritas, etc.**
