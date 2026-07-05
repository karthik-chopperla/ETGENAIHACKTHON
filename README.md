# IKIS — Industrial Knowledge Intelligence System

**Unified Asset & Operations Brain** — AI for Industrial Knowledge Intelligence (ET AI Hackathon 2026)

Ingests engineering, maintenance, safety, and compliance documents and makes their collective
intelligence queryable, actionable, and continuously updated — with real-time RAG, entity
extraction, an embedded knowledge graph, predictive maintenance intelligence, and compliance
gap detection.

## What's real vs. demo

Every tab is backed by live inference through a single NVIDIA NIM API key
(`meta/llama-3.1-70b-instruct` for reasoning, `nvidia/nv-embedqa-e5-v5` for embeddings).
If the backend is unreachable or the key isn't set, the frontend falls back to local demo data
and says so explicitly in the UI — it never silently pretends to be live.

## Project structure

```
.
├── ikis-backend/
│   ├── ikis_backend.py         FastAPI backend (RAG, entity extraction, graph, compliance)
│   ├── requirements.txt
│   ├── sample_data.py          Generates 4 sample industrial documents for testing
│   ├── sample_docs/
│   ├── .env                    NVIDIA_API_KEY, DATABASE_URL, GRAPH_PATH (not committed)
│   └── Procfile                Render web service start command
├── src/
│   ├── App.jsx                 React dashboard (5 tabs)
│   └── index.js
├── public/index.html
├── package.json
└── IKIS_demo_video.webm
```

## Quick start

**Backend**
```bash
cd ikis-backend
python -m venv venv
venv\Scripts\activate          # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
python sample_data.py          # generates sample_docs/
cp .env.example .env           # then fill in NVIDIA_API_KEY
python ikis_backend.py         # http://localhost:8000
```

**Frontend**
```bash
npm install
npm start                      # http://localhost:3000
```

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | Yes | Powers both embeddings and chat completions via NVIDIA's OpenAI-compatible NIM API (`integrate.api.nvidia.com`). Get one at [build.nvidia.com](https://build.nvidia.com). |
| `DATABASE_URL` | No | Defaults to `sqlite:///./ikis.db` |
| `GRAPH_PATH` | No | Defaults to `./knowledge_graph.gpickle` — embedded NetworkX knowledge graph, no external graph database required |
| `REACT_APP_BACKEND_URL` | No | Frontend → backend URL, defaults to `http://localhost:8000` |

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/documents/upload` | Upload a document; extracts entities, embeds, updates the knowledge graph |
| POST | `/api/query` | RAG query with citations and confidence |
| GET | `/api/maintenance/recommendations/{equipment_id}` | Graph-grounded predictive maintenance |
| GET | `/api/compliance/gaps` | Regulatory compliance gap detection |
| GET | `/api/health` | Component status |

Full interactive docs at `/docs` once the backend is running.

## Known gaps

- Computer-vision/OCR ingestion for P&IDs and scanned forms is not implemented — text/PDF only.
- Compliance mapping uses representative regulation scenarios, not a maintained full ontology of
  OISD/Factory Act/PESO.
- Not yet deployed to a public URL — see `DEPLOYMENT_GUIDE_UPDATED.md` for the Render steps
  (update the env var names there from `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` to `NVIDIA_API_KEY`).
