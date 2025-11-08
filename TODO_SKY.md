# Sky Development Checklist

**Last Updated:** 2025-11-08
**Current Phase:** Phase 0 → Phase 1 Agent Activation

---

## 🧱 PHASE 0 — PREP (STRUCTURE BEFORE CODE)

- [x] 0.1 - Create `/agent/` root folder
- [x] 0.2 - Create `/memory/` path (short + long-term folders)
- [x] 0.3 - Create `/rag/` path (local RAG bucket)
- [ ] 0.4 - Reserve Sky API route + subdomain (e.g. https://sky.alex-blythe.com/api)
- [ ] 0.5 - Add Sky to master agent registry (`agents.yaml` entry for Sky)

**Status:** 3/5 complete (60%)

---

## 🧵 PHASE 1 — IDENTITY + ACCESS

- [x] 1.1 - Create `identity_sky.txt` (preprompt)
- [x] 1.2 - Build `sky_agent_config.yaml` (now `config/sky.yaml`)
- [x] 1.3 - Add tool registry JSON Sky can read (`agent/tool_registry.json`)
- [ ] 1.4 - Create Sky's "Who am I?" self-awareness prompt
- [ ] 1.5 - Implement first RAG hook (manual) - Sky can ask: "What do I know?"

**Status:** 3/5 complete (60%)

**Next Steps:**
1. Test identity loading from `identity_sky.txt`
2. Build self-awareness query function
3. Implement basic RAG query hook

---

## 🧠 PHASE 2 — MEMORY SYSTEM

- [x] 2.1 - Create memory schema (`memory/schema.md`)
- [x] 2.2 - Implement short-term memory write function (stub in `memory_router.py`)
- [ ] 2.3 - Implement long-term commit logic with scoring
- [ ] 2.4 - Complete `sky_memory.py` helper (read/write/search/commit functions)
- [ ] 2.5 - Add "explain what you remembered and why" function (required for test M-02)

**Status:** 2/5 complete (40%)

**Blockers:**
- Need to choose vector DB for RAG (ChromaDB recommended)
- Need to implement scoring algorithm for memory promotion

**Next Steps:**
1. Finalize memory scoring algorithm (0-10 scale)
2. Implement memory rotation when short-term hits 100 entries
3. Build memory search function

---

## 🛠️ PHASE 3 — TOOL INTEGRATION

- [x] 3.1 - Create `/tools/tools_registry.json` (created as `agent/tool_registry.json`)
- [x] 3.2 - Add Sky's allowed tools to registry
- [ ] 3.3 - Add tool calling helper (`sky_tool_runner.py`)
- [ ] 3.4 - Implement tool awareness query (Sky can respond "What tools do I have?")
- [ ] 3.5 - Simulate failed tool call → verify escalation path (required for test T-05)

**Status:** 2/5 complete (40%)

**Next Steps:**
1. Build `sky_tool_runner.py` with logging
2. Implement tool permission checking
3. Create tool failure escalation path to Aegis

---

## 🧭 PHASE 4 — ORCHESTRATION BOOTSTRAP

- [ ] 4.1 - Create `sky_orchestrator.py` (handles Garmin → Reporter → TTS chain)
- [ ] 4.2 - Add failure handling + escalation (calls Aegis if needed)
- [ ] 4.3 - Add logging → `logs/sky/actions.jsonl` (required for audits)
- [ ] 4.4 - Add "explain why you ran this action" prompt (required for test R-07)

**Status:** 0/4 complete (0%)

**Dependencies:**
- Requires Phase 3 tool integration to be complete

**Next Steps:**
1. Design workflow chain architecture
2. Build workflow executor
3. Implement action logging in JSONL format

---

## ⚖️ PHASE 5 — CONSTITUTION HOOKS

- [x] 5.1 - Add authority block to Sky's config (see `config/sky.yaml`)
- [ ] 5.2 - Add "ask permission" function (for actions above authority)
- [ ] 5.3 - Add Aegis escalation stub (Aegis becomes enforcement)
- [ ] 5.4 - Implement "refuse with legal reason" response (needed for test A-01 to A-04)

**Status:** 1/4 complete (25%)

**Next Steps:**
1. Build permission checking middleware
2. Create escalation API/message format
3. Implement refusal response generator

---

## 🌐 PHASE 6 — N8N INTEGRATION (FUTURE)

- [ ] 6.1 - Design Senate orchestration architecture
- [ ] 6.2 - Build n8n workflow templates
- [ ] 6.3 - Implement voting system
- [ ] 6.4 - Add multi-agent coordination

**Status:** 0/4 complete (0%)

**Notes:** This phase is deferred until Sky passes Phase 0-5 tests

---

## 🚧 INFRASTRUCTURE TASKS

### Configuration
- [ ] Set up Cloudflare Tunnel for `sky.alex-blythe.com`
- [ ] Configure Open WebUI / Ollama endpoint
- [ ] Test API server startup
- [ ] Configure CORS for web access

### Dependencies
- [ ] Install Python packages (Flask, PyYAML, etc.)
- [ ] Choose and install vector DB (ChromaDB recommended)
- [ ] Set up embedding model (sentence-transformers)

### Testing
- [ ] Write unit tests for memory_router.py
- [ ] Write unit tests for rag_loader.py
- [ ] Write integration tests for tool execution
- [ ] Complete Phase 0 test plan (see `SKY_PHASE0_TEST_PLAN.md`)

### Documentation
- [x] Create README_SKY.md
- [x] Create repository structure
- [ ] Document API endpoints
- [ ] Write deployment guide

---

## 🐛 KNOWN ISSUES

None yet - this is a fresh build!

---

## 💡 IDEAS / ENHANCEMENTS

- [ ] Add voice wake word for hands-free interaction
- [ ] Build mobile app for morning briefing
- [ ] Add calendar integration for scheduling awareness
- [ ] Implement mood tracking alongside health data
- [ ] Add weather forecast to morning reports
- [ ] Create weekly/monthly health trend summaries

---

## 📊 OVERALL PROGRESS

**Phase 0:** 60% complete
**Phase 1:** 60% complete
**Phase 2:** 40% complete
**Phase 3:** 40% complete
**Phase 4:** 0% complete
**Phase 5:** 25% complete
**Phase 6:** 0% complete (deferred)

**Overall:** ~37% complete

---

## 🎯 NEXT PRIORITIES

1. ✅ **Complete Phase 0 infrastructure** (subdomain, agent registry)
2. ✅ **Finish Phase 1 identity loading** (test self-awareness prompts)
3. 🔄 **Implement Phase 2 memory scoring** (promotion to long-term)
4. 🔄 **Build Phase 3 tool runner** (permission checking + logging)

---

## 📝 NOTES

- Sky is the architectural template for all future agents
- Each phase builds on the previous one - don't skip ahead
- Test each phase thoroughly before moving to next
- All actions must be logged for constitutional accountability
- Memory isolation is critical - Sky cannot see other agent memories

---

**Remember:** Sky's success determines the entire multi-agent system's viability.
Take the time to do it right.
