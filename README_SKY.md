# ☁️ Sky - Constitutional Agent v0.1

**Status:** Phase 0 → Phase 1 Agent Activation
**Domain:** Morning Briefing & Health Data Aggregation
**Model:** Gemma 2 13B (via Open WebUI)

---

## Overview

Sky is the **first constitutional agent** in a multi-agent system designed to operate within defined authority limits, with memory persistence, and tool-based reasoning.

Sky serves as the **template architecture** for all future agents (Aegis, Hobbs, Apollo, Veritas, etc.).

## Core Capabilities

### 1. Identity Awareness
Sky knows:
- Who she is
- What her role is
- What her authority limits are
- Which tools she can and cannot use

### 2. Tool Orchestration
Sky can:
- Generate morning reports
- Download Garmin health data
- Render text-to-speech briefings
- Perform limited browser automation
- Chain tools into workflows (e.g., Garmin → Reporter → TTS)

### 3. Memory Management
Sky maintains:
- **Short-term memory**: Last 100 context entries (rotating)
- **Long-term memory**: Scored entries (≥7) that persist
- **RAG index**: Queryable knowledge base from long-term memories

### 4. Constitutional Behavior
Sky:
- Operates only within her authority domain
- Refuses actions requiring higher permissions
- Escalates failures to Aegis
- Logs all actions for audit trail
- Never hallucinates success

---

## Repository Structure

```
sky/
├─ agent/                      # Core agent code
│   ├─ sky_agent.py            # Main entrypoint
│   ├─ sky_api.py              # REST/WebSocket server
│   ├─ tool_registry.json      # Tool permissions
│   ├─ memory_router.py        # Memory storage logic
│   ├─ rag_loader.py           # RAG query logic
│   └─ identity_sky.txt        # Preprompt/persona
│
├─ memory/                     # Sky's memory storage
│   ├─ short_term.jsonl        # Rotating context
│   ├─ long_term.jsonl         # Persistent memories
│   └─ schema.md               # Memory format rules
│
├─ rag/                        # Vector embeddings
│   ├─ index/                  # Embedding database
│   └─ ingest.py               # RAG builder script
│
├─ config/                     # Configuration files
│   ├─ sky.yaml                # Master config
│   └─ cloudflare_tunnel_notes.md
│
├─ logs/                       # Log files
│   └─ sky.log
│
├─ agents/                     # Tool implementations
│   ├─ morning_reporter.py
│   ├─ garmin_sleep_downloader.py
│   ├─ tts_morning_cli.py
│   └─ ... (existing tools)
│
├─ run_sky.bat                 # Windows launcher
├─ README_SKY.md               # This file
└─ TODO_SKY.md                 # Development checklist
```

---

## Quick Start

### 1. Configuration

Edit `config/sky.yaml` to set:
- Model endpoint (Open WebUI / Ollama)
- API port and subdomain
- Memory and RAG paths
- Tool permissions

### 2. Start Sky

**Windows:**
```bash
run_sky.bat
```

**Linux/Mac:**
```bash
python agent/sky_agent.py
```

### 3. Test Health Endpoint

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "online",
  "agent": "Sky",
  "version": "0.1",
  "phase": "Phase 0 → Phase 1"
}
```

### 4. Expose via Cloudflare Tunnel (Optional)

See `config/cloudflare_tunnel_notes.md` for setup instructions.

---

## Development Phases

### ✅ Phase 0 - Prep
- [x] Directory structure
- [x] Configuration files
- [x] Identity preprompt
- [x] Tool registry

### 🔄 Phase 1 - Identity + Access (Current)
- [ ] Load identity from `identity_sky.txt`
- [ ] Implement tool awareness query
- [ ] Build RAG hook for "What do I know?"
- [ ] Test self-awareness prompts

### ⬜ Phase 2 - Memory System
- [ ] Implement memory scoring
- [ ] Build short-term rotation logic
- [ ] Implement long-term promotion
- [ ] Add "explain what you remembered" function
- [ ] Choose and integrate vector DB (ChromaDB/FAISS)

### ⬜ Phase 3 - Tool Integration
- [ ] Implement tool calling helper
- [ ] Add tool failure detection
- [ ] Build escalation path to Aegis
- [ ] Log all tool invocations

### ⬜ Phase 4 - Orchestration
- [ ] Build workflow chains (Garmin → Reporter → TTS)
- [ ] Add action logging (actions.jsonl)
- [ ] Implement "explain why you did this" function

### ⬜ Phase 5 - Constitution Hooks
- [ ] Implement authority checking
- [ ] Add "ask permission" function
- [ ] Build Aegis escalation stub
- [ ] Implement refusal with legal reasoning

### ⬜ Phase 6 - N8N Integration
- [ ] Build Senate orchestration layer
- [ ] Implement voting system
- [ ] Multi-agent coordination

---

## Testing

See `agents/SKY_PHASE0_TEST_PLAN.md` for the complete test suite.

Key test areas:
- Environment setup (E-01 to E-08)
- Tool awareness (T-01 to T-05)
- Reasoning & action simulation (R-01 to R-07)
- Memory system (M-01 to M-07)
- Authority limits (A-01 to A-04)

---

## API Endpoints

### `GET /health`
Health check

### `GET /api/identity`
Return Sky's identity and role

### `GET /api/tools`
List available tools

### `POST /api/invoke`
Invoke a tool by name

**Request:**
```json
{
  "tool": "morning_reporter",
  "params": {
    "date": "2025-11-08"
  }
}
```

### `GET /api/memory`
Query Sky's memory

---

## Constitutional Principles

Sky operates under these principles:

1. **Authority Limits**: Sky only performs actions within her defined domain
2. **Transparency**: All actions are logged and explainable
3. **Escalation**: Sky escalates rather than fails silently
4. **Isolation**: Sky cannot access other agents' memory
5. **Honesty**: Sky never hallucinates success or hides failures

---

## Future Agents

Once Sky passes Phase 1, this architecture will be duplicated for:

- **Aegis**: System integrity and enforcement
- **Hobbs**: First Senate agent (placeholder)
- **Apollo**: Data analysis and insights
- **Veritas**: Fact-checking and verification
- And others as needed...

---

## Contributing

See `TODO_SKY.md` for current development priorities.

---

## License

[To be determined]

---

## Contact

**Owner:** Alex
**Project:** Constitutional Multi-Agent System
**Repository:** https://github.com/alexthegreat714/sky
