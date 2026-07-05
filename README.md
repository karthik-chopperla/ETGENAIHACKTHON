# IKIS — Industrial Knowledge Intelligence System

**Unified Asset & Operations Brain** — AI for Industrial Knowledge Intelligence (ET AI Hackathon 2026)

Ingests engineering, maintenance, safety, and compliance documents — text, PDF, or a photo/scan
of a form or drawing — and makes their collective intelligence queryable, actionable, and
continuously updated. Seven capabilities, all backed by real inference against real uploaded
documents, verified end-to-end.

## What's real vs. demo

Every tab is backed by live inference through a single NVIDIA NIM API key
(`meta/llama-3.1-70b-instruct` for reasoning, `meta/llama-3.2-11b-vision-instruct` for image/OCR,
`nvidia/nv-embedqa-e5-v5` for embeddings). If the backend is unreachable or the key isn't set, the
frontend falls back to local demo data and says so explicitly in the UI — it never silently
pretends to be live.

## Capabilities

| Tab | What it does |
|---|---|
| Documents | Upload equipment manuals, maintenance logs, regulatory packs, incident/near-miss reports — as text, PDF, or a photo/scan (read via vision-model OCR, no separate OCR engine needed). Extracts equipment tags, procedures, regulations, personnel, dates on every upload and adds them to the knowledge graph. |
| Expert Query | RAG copilot — ask a question, get an answer grounded in your uploaded documents with cited sources and a confidence score. Explicitly declines (confidence 0, no fabricated sources) when a query doesn't match anything in the knowledge base. |
| Maintenance | Predictive maintenance recommendations grounded in an equipment's real document history via knowledge-graph traversal. |
| Maintenance → RCA | Multi-step Root Cause Analysis agent: three independent retrieval steps (equipment history via graph traversal, safety procedures via semantic search, regulations via semantic search) feeding one synthesis step — distinguishes immediate cause from root cause. |
| Compliance | Gap detection. Grounded in real uploaded regulatory documents when any exist (cross-referenced against operational documents); clearly labeled as a representative scenario when none have been uploaded yet. |
| Lessons Learned | Cross-document pattern detection over incident/near-miss/audit reports — surfaces systemic root causes that no single-document review would catch, with a proactive recommended action. |
| Overview | KPIs and workflow summary. |

## Project structure

```
.
├── ikis-backend/
│   ├── ikis_backend.py         FastAPI backend (RAG, OCR, graph, RCA, lessons learned, compliance)
│   ├── requirements.txt
│   ├── sample_data.py          Generates 7 sample industrial documents for testing
│   ├── evaluate_benchmark.py   Benchmark question set + timed evaluation against the live API
│   ├── BENCHMARK_RESULTS.md    Latest benchmark run output
│   ├── sample_docs/
│   ├── .env                    NVIDIA_API_KEY, DATABASE_URL, GRAPH_PATH (not committed)
│   └── Procfile                Render web service start command
├── src/
│   ├── App.jsx                 React dashboard (7 tabs, mobile-responsive)
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

**Run the benchmark** (after uploading all 7 sample_docs/ files via the Documents tab or curl):
```bash
cd ikis-backend
python evaluate_benchmark.py   # writes BENCHMARK_RESULTS.md
```

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | Yes | Powers embeddings, chat completions, and vision/OCR via NVIDIA's OpenAI-compatible NIM API (`integrate.api.nvidia.com`). Get one at [build.nvidia.com](https://build.nvidia.com). |
| `DATABASE_URL` | No | Defaults to `sqlite:///./ikis.db` |
| `GRAPH_PATH` | No | Defaults to `./knowledge_graph.gpickle` — embedded NetworkX knowledge graph, no external graph database required |
| `REACT_APP_BACKEND_URL` | No | Frontend → backend URL, defaults to `http://localhost:8000` |

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/documents/upload` | Upload a document (text/PDF/image); extracts entities, embeds, updates the knowledge graph |
| POST | `/api/query` | RAG query with citations and confidence |
| GET | `/api/maintenance/recommendations/{equipment_id}` | Graph-grounded predictive maintenance |
| GET | `/api/maintenance/rca/{equipment_id}` | Multi-step Root Cause Analysis |
| GET | `/api/compliance/gaps` | Regulatory compliance gap detection |
| GET | `/api/lessons-learned/patterns` | Cross-document failure pattern detection |
| GET | `/api/health` | Component status |

Full interactive docs at `/docs` once the backend is running.

## Evaluation

`ikis-backend/BENCHMARK_RESULTS.md` has the latest run: 8 questions grounded in the actual sample
corpus (7 real facts + 1 negative control), scored by keyword coverage, with response times and a
deliberately honest comparison against a naive keyword-search baseline — this is an automated
regression proxy, not a substitute for real domain-expert grading.

## Known gaps

- True P&ID schematic computer vision (symbol/line/instrument recognition) is not implemented.
  Image uploads are read via a vision-language model for text/tag transcription — genuine OCR and
  document intelligence, but not diagram-structure parsing.
- No QMS system integration — there's no specific target system named in scope, and none is wired up.
- Compliance mapping is grounded in whatever regulatory documents you've actually uploaded; without
  any uploaded, it falls back to clearly-labeled representative scenarios rather than a maintained
  ontology of the full text of OISD/Factory Act/PESO.
- The benchmark set is small (8 questions) and automated (keyword match), not a large domain-expert-
  graded suite.
- Not yet deployed to a public URL — see `DEPLOYMENT_GUIDE_UPDATED.md` for the Render steps
  (update the env var names there from `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` to `NVIDIA_API_KEY`).
