# Genie AI — MARRE (Multi-Agent Research & Reporting Engine)

Automates the **Gather → Compare → Report** workflow using LangGraph, FastAPI, ChromaDB, PostgreSQL, and HackerNews community signals.

## Architecture

```
POST /research/stream (SSE)
          │
          ▼
      LangGraph
  ┌──────────────────────────────────────────────────┐
  │  classifier → planner → gatherer                 │
  │                           ├── ChromaDB RAG       │
  │                           └── HackerNews Algolia │
  │               → comparator → writer              │
  │               → scorer → persist                 │
  └──────────────────────────────────────────────────┘
          │
          ▼
  ResearchReport (JSON) + live SSE pipeline trace
```

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph (functional API — `@task`, `@entrypoint`) |
| API | FastAPI + Uvicorn |
| Vector Store | ChromaDB (local persistent) |
| Database | PostgreSQL 16 (Docker) + SQLAlchemy + Alembic |
| LLMs | GPT-4o (all nodes) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Community Search | HackerNews via Algolia public API |
| UI | Streamlit (live SSE pipeline trace) |

## Phase Status

| Phase | Status | Scope |
|---|---|---|
| 1 | ✅ Complete | Local RAG, LangGraph graph, FastAPI, PostgreSQL, Streamlit UI |
| 2 | 🔄 Active | HackerNews ✅ · Tavily (parked) · Firecrawl (parked) |
| Prod | 🔜 Next | Retries, auth, rate limiting, observability, deployment hardening |
| 3 | Pending | Langfuse/Langsmith observability |
| 4 | Pending | RAGAS evals, safety guardrails |

## Quick Start

### 1. Install dependencies
```bash
pip install -e .
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in OPENAI_API_KEY
```

### 3. Start all services
```bash
docker compose up --build -d
```
- API (with auto-migration) → `http://localhost:8000`
- UI → `http://localhost:8501`
- Docs → `http://localhost:8000/docs`

### 4. Ingest local knowledge base
```bash
python scripts/ingest.py
```

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/research` | Sync research run |
| `POST` | `/research/stream` | SSE streaming run (used by UI) |
| `GET` | `/runs/recent` | Last 3 runs with trace IDs |

### Example
```bash
curl -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare AcmeDoc AI and PaperMind AI for enterprise document processing"}'
```

## Project Structure

```
src/
├── agents/      # LangGraph @task nodes (classifier, planner, gatherer, comparator, writer, scorer, persist)
├── api/         # FastAPI app, routes (research, stream, runs)
├── db/          # SQLAlchemy session + Alembic migrations
├── rag/         # ChromaDB ingestion (loaders, embeddings, client, retriever)
├── schemas/     # Pydantic models (ResearchReport, AgentRunResult)
├── tools/       # External tools (hackernews.py)
├── ui/          # Streamlit app
└── graph.py     # LangGraph @entrypoint
data/
├── research_pack/sources/   # 5 source files (A–E): HTML, CSV, TXT, PDF
└── *.json                   # Output schemas
docs/            # TODOs, ideas, design notes (committed)
working/         # Session logs, run history (gitignored)
scripts/         # ingest.py, start.sh
alembic/         # DB migrations
```

## Development Notes
- Working memory → `working/` (gitignored)
- Design docs, TODOs → `docs/` (committed)
- Never commit `.env`
- DB migrations run automatically on API container start
- HackerNews search uses Algolia's public API — no key required
