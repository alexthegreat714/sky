# Sky RAG + Chat Interface (v5)

Sky mirrors Aegis Phase 5.2 with its own RAG store, DeepRouter, and metrics.

## Endpoints
- `/rag/write` – POST JSON: {"text","source","kind","priority"}
- `/rag/search` – POST JSON: {"query","top_k","min_priority"}
- `/rag/count` – POST JSON: {"where":{...}}
- `/rag/list` – GET ids only
- `/rag/get` – POST details
- `/rag/delete` – POST filtered delete
- `/chat` – intent-routed hybrid reasoning with DeepCoder support

### Data Path
`C:\Users\blyth\Desktop\Engineering\rag_data\Sky\`

### Test Commands
```bash
curl -X POST http://127.0.0.1:5011/rag/write -H "Content-Type: application/json" -d "{\"text\":\"Morning Agent schedule: 08:00–12:00 data sync.\",\"source\":\"ops\",\"kind\":\"schedule\",\"priority\":0.9}"
curl -X POST http://127.0.0.1:5011/rag/search -H "Content-Type: application/json" -d "{\"query\":\"morning plan\",\"top_k\":3,\"min_priority\":0.8}"
curl -X POST http://127.0.0.1:5011/rag/count -H "Content-Type: application/json" -d "{\"where\":{\"source\":\"ops\"}}"
curl -X POST http://127.0.0.1:5011/chat -H "Content-Type: application/json" -d "{\"message\":\"What’s the morning plan?\"}"
```
