# Agent Template Guide
Create via tool:
  python -m src.tools.create_agent --name apollo --role "Finance & Markets"

Each agent gets:
- memory/   (short-term logs, vector index folder)
- rag/      (per-agent ingest/query utilities)
- main.py   (entry + describe() method)

Later:
- Expose agent service via FastAPI
- Attach to Senate bus
