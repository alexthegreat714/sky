# Changelog

All notable changes to Sky will be documented in this file.

## [Phase 4] - 2025-11-08

### Added

#### Task Runner (`sky/tasks/task_runner.py`)
- Async scheduler with configurable tick interval (default 30s)
- JSON-based task queue (`sky/tasks/queue.json`)
- Human-readable HH:MM schedule parsing
- Constitutional authority enforcement
- FastAPI endpoints for task management:
  - `GET /tasks/list` - List all tasks
  - `POST /tasks/add` - Add new task
  - `POST /tasks/enable` - Enable task by name
  - `POST /tasks/disable` - Disable task by name
  - `POST /tasks/run_now` - Execute task immediately
  - `DELETE /tasks/remove` - Remove task
- CLI support: `python -m sky.tasks.task_runner`
- Comprehensive logging to `logs/task_runner.log`
- Tests: `tests/test_task_runner.py`

#### Memory Inspector (`sky/memory/inspector.py`)
- Browse short-term and long-term memory stores
- Promote memories to RAG vectorstore
- Delete specific memories by ID
- Memory statistics and metadata
- FastAPI endpoints:
  - `GET /memory/list?type=short|long` - List memories
  - `GET /memory/stats` - Get statistics
  - `GET /memory/get?id=<id>` - Get specific memory
  - `POST /memory/promote?id=<id>` - Promote to long-term + RAG
  - `DELETE /memory/delete?id=<id>` - Delete memory
- CLI support: `python -m sky.memory.inspector`
- Audit logging to `logs/memory_audit.log`
- Tests: `tests/test_memory_inspector.py`

#### Self-Improvement Tool (`sky/self/self_improve.py`)
- OCR support for PDFs and images (pytesseract)
- Web scraping with requests + BeautifulSoup
- Intelligent text chunking with sentence boundary detection
- Archive management (`sky/self/archive/`)
- RAG vectorstore integration
- Comprehensive audit logging (`sky/self/audit_log.jsonl`)
- Constitutional authority enforcement (`self_enhancement` permission)
- FastAPI endpoints:
  - `POST /self/ingest_ocr` - Upload and OCR file
  - `POST /self/ingest_scrape` - Scrape and ingest URL
  - `POST /self/ingest_text` - Ingest raw text
  - `GET /self/audit_log` - Get ingestion audit log
- CLI support: `python -m sky.self.self_improve`
- Tests: `tests/test_self_improve.py`

### Changed
- Updated `src/governance/constitution.py`:
  - Added `"self_enhancement"` to allowed actions
  - Enables constitutional oversight for knowledge acquisition

### Documentation
- Updated `README_SKY.md`:
  - Added Phase 4 Tools section
  - Documented all new CLI commands and API endpoints
- Added `CHANGELOG.md` (this file)

### Dependencies
New optional dependencies for Phase 4 tools:
- `pytesseract` - OCR engine
- `pdf2image` - PDF to image conversion
- `pillow` - Image processing
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing

Install with:
```bash
pip install pytesseract pdf2image pillow requests beautifulsoup4
```

---

## [Phase 3] - 2025-11-07

### Added
- Memory promotion engine (`src/memory/promoter.py`)
- Senate message bus (`src/senate_bus/broker.py`)
- Hobbs agent inbox (`src/agents/hobbs/inbox.py`)
- Tool registry with auto-discovery (`src/sky/tool_registry.py`)
- Webhook API endpoints (`src/sky/service.py`)
- Governance and constitution scaffolds
- RAG integration scaffolds

### Documentation
- `docs/TOOLS.md` - Tool creation and discovery guide
- `docs/WEBHOOK_API.md` - API reference
- `docs/MEMORY_PROMOTION.md` - Memory promotion flow
- `docs/SENATE_MESSAGE_FLOW.md` - Inter-agent messaging

---

## [Phase 2] - 2025-11-06

### Added
- Brain integration (`agent/sky_brain.py`)
- LLM integration with OWUI (`agent/sky_llm.py`)
- Memory scoring (`agent/memory_scoring.py`)
- Tools runner (`agent/sky_tools_runner.py`)
- Logger (`agent/logger.py`)

---

## [Phase 1] - 2025-11-05

### Added
- Basic repository structure
- Configuration system (`config/sky.yaml`)
- Identity definition (`agent/identity_sky.txt`)
- FastAPI service scaffold (`agent/sky_api.py`)
- Memory and RAG directory structure

---

## [Phase 0] - 2025-11-04

### Added
- Initial project setup
- Test plan (`agents/SKY_PHASE0_TEST_PLAN.md`)
- Build plan (`agents/SKY_BUILD_PLAN_V0.1.md`)
- Repository structure design
