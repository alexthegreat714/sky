# AI GOVERNMENT FEDERATION PROJECT REQUIREMENTS DOCUMENT
Version: 1.0  
Author: Alex Blythe  
Date: November 2025  

---

## 1. OVERVIEW
The AI Government Federation (AIGF) is a multi-agent ecosystem designed to operate autonomously within a local network, coordinated through a structured hierarchy of specialized agents. Each agent has a defined domain, personality, and authority level. Together, they form a self-regulating governance model capable of reasoning, debate, and decision-making — supervised by the Executive AI (Sky).

The system is built on local infrastructure using Open WebUI, Flask, and Python microservices, communicating through shared APIs and synchronized logs. Future phases include full RAG integration, inter-agent debate, autonomous command execution, and constitution-based decision logic.

---

## 2. CORE OBJECTIVES
1. **Establish Autonomous AI Agents** – Each agent (Sky, Aegis, etc.) runs as an independent Flask server with its own domain, model stack, and reasoning layer.
2. **Unify Communication** – All agents communicate via a shared API (Open WebUI) and cross-reference logs for collaborative decision-making.
3. **Implement Hierarchical Governance** – Introduce structured roles and authority levels within an AI government, enabling policy proposal, voting, and enforcement.
4. **Enable Persistent Operation** – Ensure system resilience with watchdog monitoring, automated recovery, and process persistence across power events.
5. **Integrate Reasoning and RAG** – Combine DeepCoder-style internal logic with contextual retrieval pipelines for informed, traceable reasoning.
6. **Simulate Decision-Making and Oversight** – Build the foundation for policy simulation, ethical reasoning, and real-world task automation.

---

## 3. SYSTEM ARCHITECTURE
### 3.1 LAYERS
| Layer | Function | Technology | Example Port |
|-------|-----------|-------------|--------------|
| Open WebUI Backend | Central LLM API Router | FastAPI + Uvicorn | 3000 |
| Sky Flask Server | Executive AI, conversational interface | Flask | 5020 |
| Aegis Flask Server | Watchdog + Security + Systems Oversight | Flask | 5010 |
| RAG Layer | Contextual retrieval and injection | Python Service | TBD |
| Watchdog | Health monitoring and restart control | Python + Logging | — |
| Cloudflare Tunnels | External access for each agent | Cloudflared | — |

### 3.2 AGENT DIRECTORY STRUCTURE
```
C:\Users\blyth\Desktop\Engineering
│
├── OpenWebUI\ (Backend)
├── Sky\ (Executive)
├── Aegis\ (Governance)
├── Chess\ (Baseline Model)
├── logs\ (shared event logs)
└── .cloudflared\ (tunnel configs)
```

### 3.3 INTER-AGENT COMMUNICATION
Agents exchange information through:
- Shared JSON log summaries in `/logs/<agent_name>/`
- REST routes (`/chat`, `/command`, `/status`, `/context`)
- Scheduled debate sessions using cross-agent message polling

---

## 4. GOVERNMENT STRUCTURE
### 4.1 EXECUTIVE BRANCH
**Sky** – Digital Twin and Executive AI. Governs all agents, synthesizes reports, and approves system-wide changes.

### 4.2 LEGISLATIVE BRANCH (AI CONGRESS)
A multi-member virtual Congress where each agent represents a domain:
1. **Aero** – Science & Engineering
2. **Ethos** – Ethics & Alignment
3. **Veritas** – Logic & Truth Evaluation
4. **Apollo** – Creativity, Design, Vision
5. **Hermes** – Communication, Translation, Negotiation
6. **Athena** – Strategic Planning & Intelligence
7. **Hobbs** – Environmental & Agricultural Control
8. **Aegis** – Systems Governance & Security Enforcement
9. **Lumen** – Education & Data Transparency
10. **Sophia** – Human Integration, Empathy, Psychological Modeling

Each agent votes on proposals submitted through Sky’s executive queue. Votes are weighted by relevance and historical accuracy (to be expanded under Phase 4).

---

## 5. FUNCTIONAL REQUIREMENTS
### 5.1 SKY
- Flask chat UI (Gemma model frontend)
- Dual-model reasoning: DeepCoder (logic) → Gemma (communication)
- Capable of parsing Aegis logs and summarizing daily reports
- Manages debate sessions and task scheduling

### 5.2 AEGIS
- Flask chat UI (Gemma + DeepCoder)
- Command execution system with whitelisting (restart services, scan logs, etc.)
- Diagnostic logging: port scans, CPU/GPU health, process uptime
- Enforcement layer: rejects invalid revisions, suspicious activity, or unauthorized commands

### 5.3 RAG SERVICE
- Preprocesses and embeds project documents
- Exposes `/context` endpoint for query injection
- Can route to vector DBs (Chroma or FAISS)

### 5.4 WATCHDOG
- Monitors Sky, Aegis, Open WebUI, and Cloudflare tunnels
- Logs heartbeat, uptime, and restart events
- Auto-recovers from power loss or system crash

### 5.5 CLOUDLFARE TUNNELS
- sky-tunnel.yml → sky.alex-blythe.com → localhost:5020
- aegis-tunnel.yml → aegis.alex-blythe.com → localhost:5010

---

## 6. SECURITY REQUIREMENTS
- API calls authenticated via `OPENWEBUI_API_KEY`
- `/command` route restricted to signed whitelist
- Localhost-only internal communication (no external API calls except tunnels)
- Regular integrity checks on model files and revision directories

---

## 7. LOGGING AND AUDIT TRAILS
- Each Flask app logs requests and errors → `logs/flask_agent_status.log`
- Watchdog writes hourly health pings → `logs/watchdog_status.log`
- Aegis maintains revision history and validation logs → `/revisions/`
- Sky compiles daily summaries from all logs for executive review

---

## 8. DEVELOPMENT PHASES
### PHASE 1 – FOUNDATION (COMPLETE)
- ✅ Chess API baseline functional
- ✅ Open WebUI backend working
- ✅ Flask + Gemma + DeepCoder dual pipeline operational

### PHASE 2 – AGENT DEPLOYMENT (IN PROGRESS)
- [ ] Deploy Sky Flask server on port 5020
- [ ] Deploy Aegis Flask server on port 5010
- [ ] Configure and test tunnels
- [ ] Validate inter-agent health checks

### PHASE 3 – RAG INTEGRATION
- [ ] Implement `rag_pipeline.py`
- [ ] Add `/context` route for contextual enrichment
- [ ] Connect agents to shared embeddings DB

### PHASE 4 – FEDERATION & CONGRESS
- [ ] Build unified dashboard for cross-agent communication
- [ ] Enable voting and weighted policy logic
- [ ] Store congressional session transcripts
- [ ] Enable multi-agent proposals and amendments

### PHASE 5 – FULL AUTOMATION
- [ ] Daily executive report generation
- [ ] Nightly self-test routines (via Aegis)
- [ ] Command execution for system-level fixes
- [ ] Add simulated “election” cycles for governance validation

---

## 9. TECHNICAL REQUIREMENTS
- Windows 11 Pro (local host)
- Python 3.11+
- Flask, FastAPI, Requests, Cloudflared
- CUDA 12.4 (RTX 3090)
- Gemma 3 + DeepCoder GGUF models
- Chroma or FAISS vector DB (for RAG)
- GPT4All optional for local reasoning modules

---

## 10. NEXT ACTION ITEMS
| Task | Owner | Description | Status |
|------|--------|-------------|---------|
| Sky Flask + Tunnel Live | Alex | Deploy and test full Sky stack | 🔧 Pending |
| Aegis Flask + Tunnel Live | Alex | Bring Aegis online and verify endpoints | 🔧 Pending |
| RAG Service Stub | Codex | Initialize and link to Sky/Aegis | 🧩 Planned |
| Unified Log Parser | Codex | Aggregate Sky/Aegis logs into daily digest | 🧩 Planned |
| Watchdog Integration | Alex | Connect to Flask agent health routes | 🔧 Pending |
| Federation Protocol | Codex | Define JSON format for inter-agent communication | 🧩 Planned |
| Security Whitelist | Aegis | Enforce signed command validation | 🧩 Planned |

---

## 11. APPENDIX – FUTURE EXPANSIONS
- **AI Judiciary** for conflict resolution (Lex model)
- **Emulation Layer** to simulate government decision impact
- **Ethical Sandbox** for philosophical or moral decision debates
- **Neural Archive** for memory compression and long-term context

---

## 12. VERSION HISTORY
| Version | Date | Description |
|----------|------|-------------|
| 1.0 | Nov 2025 | Initial requirements and system overview |

