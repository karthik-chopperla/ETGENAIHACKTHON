# IKIS — Industrial Knowledge Intelligence System

**Unified Asset & Operations Brain** — AI for Industrial Knowledge Intelligence (ET AI Hackathon 2026)

Ingests engineering, maintenance, safety, and compliance documents — text, PDF, or a photo/scan
of a form or drawing — and makes their collective intelligence queryable, actionable, and
continuously updated. Eight capabilities, all backed by real inference against real uploaded
documents, verified end-to-end (12/12 on the multi-endpoint benchmark).

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
| Compliance → Quality Deviations | Flags measurable parameters (vibration, temperature, etc.) explicitly reported as deviating from a stated baseline in uploaded inspection/maintenance records, with escalating severity — grounded in real numbers, never invented. |
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
├── render.yaml                  Render Blueprint — deploys both services from one file
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
| GET | `/api/documents` | List every document actually in the knowledge base |
| POST | `/api/query` | RAG query with citations and confidence |
| GET | `/api/maintenance/recommendations/{equipment_id}` | Graph-grounded predictive maintenance |
| GET | `/api/maintenance/rca/{equipment_id}` | Multi-step Root Cause Analysis |
| GET | `/api/compliance/gaps` | Regulatory compliance gap detection |
| GET | `/api/quality/deviations` | Measurable quality deviation flagging |
| GET | `/api/lessons-learned/patterns` | Cross-document failure pattern detection |
| GET | `/api/health` | Component status |

Full interactive docs at `/docs` once the backend is running.

## Evaluation

`ikis-backend/BENCHMARK_RESULTS.md` has the latest run: **12/12 passed** across all five AI-backed
capabilities (RAG query, maintenance recommendations, RCA, compliance, lessons learned), grounded
in the actual sample corpus, scored by keyword/content coverage, with response times and a
deliberately honest comparison against a naive keyword-search baseline. It also documents a real
finding: under sustained heavy testing, response times degraded to 30-140s due to shared free-tier
NVIDIA API rate limiting — correctness held throughout, but this is the actual scalability
bottleneck, not the application code (which was separately verified to stay responsive to other
requests while a slow LLM call is in flight, via `asyncio.to_thread`). This is an automated
regression proxy, not a substitute for real domain-expert grading.

## Deployment

`render.yaml` is a Render Blueprint that declares both services (backend + static frontend) for a
near-one-click deploy — connect the repo under Render's Blueprint flow and fill in `NVIDIA_API_KEY`
when prompted. It hasn't been run against a live Render account from here, so double-check field
names against Render's current Blueprint docs on first use. `DEPLOYMENT_GUIDE_UPDATED.md` has the
manual step-by-step alternative (update its env var names from `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`
to `NVIDIA_API_KEY`).

## Known gaps

- True P&ID schematic computer vision (ISA symbol libraries, instrument bubbles, line-type/pipe-class
  recognition) is not implemented. What does work, tested on a synthetic diagram: the vision model
  correctly read equipment tags **and** inferred basic flow relationships (e.g. `TANK-101 -> PUMP-001
  -> VLV-201 -> TANK-102`) from a simple layout — real partial diagram-structure understanding, not
  just text transcription, but unvalidated against dense, real industry-standard drawings.
- No QMS system integration — there's no specific target system named in scope. What's built instead
  is quality-deviation flagging from uploaded records (see Compliance tab), which covers the brief's
  "flagging quality deviations" language without a specific external system to integrate with.
- Compliance mapping is grounded in whatever regulatory documents you've actually uploaded; without
  any uploaded, it falls back to clearly-labeled representative scenarios rather than a maintained
  ontology of the full text of OISD/Factory Act/PESO.
- The benchmark set is still automated (keyword/content match), not a large domain-expert-graded suite.
- Not yet deployed to a public URL — `render.yaml` is ready but unexecuted; needs your Render account.
