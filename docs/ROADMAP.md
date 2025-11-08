# Sky Development Roadmap

## Overview

Sky is evolving through multiple phases from a basic constitutional agent to a fully-featured, self-improving knowledge system with multi-agent coordination.

---

## Phase 0: Foundation ✅ COMPLETE

**Goal:** Establish repository structure and initial scaffolds

**Completed:**
- [x] Repository structure
- [x] Configuration system (`config/sky.yaml`)
- [x] Test plan documentation
- [x] Build plan documentation
- [x] Initial .gitignore and requirements.txt

**Date:** 2025-11-04

---

## Phase 1: Identity & Basic API ✅ COMPLETE

**Goal:** Basic agent identity and REST API

**Completed:**
- [x] Identity definition (`agent/identity_sky.txt`)
- [x] FastAPI service scaffold (`agent/sky_api.py`)
- [x] Basic health endpoint
- [x] Memory and RAG directory structure
- [x] Tool registry scaffold

**Date:** 2025-11-05

---

## Phase 2: Brain & LLM Integration ✅ COMPLETE

**Goal:** Core reasoning engine with LLM backend

**Completed:**
- [x] Brain integration (`agent/sky_brain.py`)
- [x] LLM integration with Open WebUI (`agent/sky_llm.py`)
- [x] Memory scoring system (`agent/memory_scoring.py`)
- [x] Tools runner with subprocess execution (`agent/sky_tools_runner.py`)
- [x] JSONL action logger (`agent/logger.py`)
- [x] Intent routing (tool/memory/LLM)

**Date:** 2025-11-06

---

## Phase 3: Governance & RAG ✅ COMPLETE

**Goal:** Constitutional authority and knowledge retrieval

**Completed:**
- [x] Governance framework (`src/governance/constitution.py`, `authority_gate.py`)
- [x] Memory promotion engine (`src/memory/promoter.py`)
- [x] Tool registry with auto-discovery (`src/sky/tool_registry.py`)
- [x] Webhook API (`src/sky/service.py`)
- [x] Senate message bus (`src/senate_bus/broker.py`)
- [x] Hobbs agent inbox (`src/agents/hobbs/inbox.py`)
- [x] RAG scaffolds (`src/rag/shared_ingest.py`, `query.py`)
- [x] Orchestrator v1 (`src/sky/orchestrator.py`)
- [x] Status tracking (`status/sky_heartbeat.json`, `sky_last_action.json`)

**Documentation:**
- [x] `docs/TOOLS.md`
- [x] `docs/WEBHOOK_API.md`
- [x] `docs/MEMORY_PROMOTION.md`
- [x] `docs/SENATE_MESSAGE_FLOW.md`
- [x] `docs/ORCHESTRATOR.md`

**Date:** 2025-11-07

---

## Phase 4: Advanced Tools & Self-Improvement ✅ COMPLETE

**Goal:** Internal task scheduler, memory management, and knowledge acquisition

**Completed:**
- [x] Task runner with scheduler (`sky/tasks/task_runner.py`)
  - [x] JSON-based task queue
  - [x] HH:MM schedule parsing
  - [x] FastAPI endpoints
  - [x] CLI interface
  - [x] Constitutional authority enforcement
  - [x] Tests (`tests/test_task_runner.py`)

- [x] Memory inspector (`sky/memory/inspector.py`)
  - [x] Browse short/long-term memories
  - [x] Promote to RAG
  - [x] Delete memories
  - [x] Statistics and metadata
  - [x] FastAPI endpoints
  - [x] CLI interface
  - [x] Audit logging
  - [x] Tests (`tests/test_memory_inspector.py`)

- [x] Self-improvement tool (`sky/self/self_improve.py`)
  - [x] OCR PDFs and images (pytesseract)
  - [x] Web scraping (BeautifulSoup)
  - [x] Text chunking with sentence boundaries
  - [x] RAG vectorstore integration
  - [x] Archive management
  - [x] Audit logging
  - [x] FastAPI endpoints
  - [x] CLI interface
  - [x] Constitutional authority (`self_enhancement`)
  - [x] Tests (`tests/test_self_improve.py`)

**Documentation:**
- [x] Updated `README_SKY.md` with Phase 4 tools
- [x] Added `CHANGELOG.md`
- [x] Updated `src/governance/constitution.py` with `self_enhancement`
- [x] Created `docs/ROADMAP.md` (this file)

**Date:** 2025-11-08

---

## Phase 5: Production Readiness ⬜ PLANNED

**Goal:** Make Sky production-ready with robustness and monitoring

**Planned:**
- [ ] Error recovery and retry logic
- [ ] Comprehensive test coverage (>80%)
- [ ] Performance monitoring and metrics
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Production configuration management
- [ ] Log rotation and management
- [ ] Health checks and alerting
- [ ] API rate limiting
- [ ] Authentication and authorization
- [ ] Secrets management
- [ ] Database migrations for persistent storage

**Target Date:** TBD

---

## Phase 6: RAG Enhancement ⬜ PLANNED

**Goal:** Full ChromaDB integration with semantic search

**Planned:**
- [ ] Implement ChromaDB backend (`src/rag/shared_ingest.py`)
- [ ] Sentence embeddings (sentence-transformers)
- [ ] Semantic search API
- [ ] RAG query optimization
- [ ] Memory consolidation
- [ ] Duplicate detection
- [ ] Vector index management
- [ ] Hybrid search (keyword + semantic)

**Dependencies:**
- `chromadb`
- `sentence-transformers`

**Target Date:** TBD

---

## Phase 7: Multi-Agent Coordination ⬜ PLANNED

**Goal:** Senate voting system and agent orchestration

**Planned:**
- [ ] Senate bus upgrade to Redis/RabbitMQ
- [ ] Voting protocol implementation
- [ ] Multi-agent task delegation
- [ ] Conflict resolution
- [ ] Agent discovery and registration
- [ ] Cross-agent memory sharing (selective)
- [ ] N8N workflow integration
- [ ] Event-driven architecture

**Target Date:** TBD

---

## Phase 8: Advanced Capabilities ⬜ PLANNED

**Goal:** Advanced reasoning and autonomous operation

**Planned:**
- [ ] Chain-of-thought reasoning
- [ ] Self-reflection and critique
- [ ] Planning and goal decomposition
- [ ] Tool composition and chaining
- [ ] Dynamic tool generation
- [ ] Learning from feedback
- [ ] Anomaly detection
- [ ] Predictive scheduling

**Target Date:** TBD

---

## Future Agents

Once Sky is mature, replicate architecture for:

- **Aegis**: System integrity and enforcement
- **Hobbs**: Data analysis and reporting
- **Apollo**: Strategic planning
- **Veritas**: Fact-checking and verification
- **Oracle**: Predictive analytics
- **Sentinel**: Security monitoring

---

## Metrics & Success Criteria

### Phase Completion Criteria:
- All planned features implemented
- Tests passing with >70% coverage
- Documentation complete
- No critical bugs
- User acceptance testing passed

### System Health Metrics:
- **Uptime:** >99.5%
- **Response time:** <500ms for API calls
- **Memory usage:** <2GB RAM
- **Task success rate:** >95%
- **Constitutional compliance:** 100%

---

## Dependencies Timeline

### Immediate (Phase 5-6):
- Docker & docker-compose
- pytest & pytest-cov (testing)
- chromadb & sentence-transformers (RAG)
- prometheus & grafana (monitoring)

### Future (Phase 7-8):
- Redis or RabbitMQ (message bus)
- PostgreSQL (persistent storage)
- Kubernetes (orchestration)
- n8n (workflow automation)

---

## Known Limitations

### Current:
- RAG is scaffolded (not fully functional)
- No authentication on APIs
- Single-threaded task execution
- Limited error recovery
- No persistent database

### Planned Fixes:
- See Phase 5-6 roadmap items

---

## Contributing

To contribute to Sky development:
1. Check current phase in this roadmap
2. Pick an unassigned task
3. Create feature branch: `feature/phase-X-task-name`
4. Implement with tests
5. Update documentation
6. Submit PR with phase reference

---

## Questions & Feedback

For roadmap questions or suggestions:
- Create GitHub issue with `roadmap` label
- Discuss in development planning sessions
- Contact: Alex (project owner)

---

**Last Updated:** 2025-11-08 (Phase 4 completion)
