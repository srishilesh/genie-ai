# Genie AI — MARRE (Multi-Agent Research & Reporting Engine)

Automates the **Gather → Compare → Report** workflow using LangGraph, FastAPI, ChromaDB, PostgreSQL, and HackerNews community signals.

## Pipeline

```
POST /research/stream (SSE)
          │
          ▼
      LangGraph
  ┌─────────────────────────────────────────────────────────────────┐
  │  planner   → sub-questions (1 LLM call)                        │
  │  gatherer  → HN API fetch + index                              │
  │               local ChromaDB retrieval (per sub-question)      │
  │               HN ChromaDB retrieval   (per sub-question)       │
  │               avg distance comparison → pick better source     │
  │  comparator → identify agreements & conflicts across chunks    │
  │  writer     → ResearchReport JSON (GPT-4o)                     │
  │  scorer     → structural score + LLM judge → composite 0–1    │
  │    └── if confidence < 0.7 → replan + retry (max 1)           │
  │  persist    → PostgreSQL (fallback: working/runs.jsonl)        │
  └─────────────────────────────────────────────────────────────────┘
          │
          ▼
  ResearchReport (JSON) + live SSE pipeline trace
```

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph (functional API — `@task`, `@entrypoint`) |
| API | FastAPI + Uvicorn |
| Vector Store | ChromaDB (local persistent, 2 collections) |
| Database | PostgreSQL 16 (Docker) + SQLAlchemy + Alembic |
| LLMs | GPT-4o (all nodes) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Community Search | HackerNews via Algolia public API |
| Observability | LangSmith (all nodes + HN API traced) |
| UI | Streamlit (live SSE pipeline trace) |

## Phase Status

| Phase | Status | Scope |
|---|---|---|
| 1 | ✅ Complete | Local RAG, LangGraph graph, FastAPI, PostgreSQL, Streamlit UI |
| 2 | ✅ Complete | HackerNews live fetch + index + RAG, LLM source selection, retry logic |
| 3 | ✅ Complete | LangSmith observability — all nodes + HN API calls traced |
| Prod | 🔜 Next | Auth, rate limiting, structured logging, RAGAS evals |

## Quick Start

### 1. Configure environment
```bash
cp .env.example .env
# Fill in OPENAI_API_KEY, LANGSMITH_API_KEY (optional)
```

### 2. Start all services
```bash
docker compose up --build -d
```
- API → `http://localhost:8000`
- UI  → `http://localhost:8501`
- Docs → `http://localhost:8000/docs`

### 3. Ingest local knowledge base
```bash
python scripts/ingest.py
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/research` | Sync research run |
| `POST` | `/research/stream` | SSE streaming run (used by UI) |
| `GET` | `/runs/recent` | Last N runs with trace IDs |
| `GET` | `/hackernews/search` | Raw HN Algolia search |
| `POST` | `/hackernews/index` | Search + index HN results |
| `GET` | `/hackernews/retrieve` | Semantic retrieval from HN collection |

### Example
```bash
curl -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "python and ruby market trends 2024"}'
```

## Source Selection Logic

Every query hits both sources. The better one wins:

1. **HN API** — fetches live stories, indexes into `marre_hn` ChromaDB collection (up to 3 retries with query variations if 0 results)
2. **Local RAG** — retrieves from `marre_phase1` collection (sources A–E: HTML, CSV, TXT, PDF)
3. Both are queried per sub-question → avg cosine distance compared → lower distance wins

## Confidence Scoring

Composite score = **40% structural + 60% LLM judge**

- **Structural**: sources cited, comparisons with data, findings count, recommendation, citations, open-question penalty
- **LLM judge**: GPT-4o rates query relevance, factual grounding, and coverage (each 0–1)
- If composite < 0.7 → replan with focused sub-questions → retry once → use better result

## Project Structure

```
src/
├── agents/      # planner, gatherer, comparator, writer, scorer, persist
├── api/         # FastAPI routes (research, stream, runs, hackernews) + utils
├── db/          # SQLAlchemy session
├── prompts.py   # All LLM system + user prompts (configurable)
├── rag/         # ChromaDB client, embeddings, loaders, retriever
├── schemas/     # Pydantic models — ResearchReport, LLM request/response schemas
├── tools/       # hackernews.py — Algolia search, relevance filter, chunking
├── ui/          # Streamlit app
└── graph.py     # LangGraph @entrypoint
data/
├── research_pack/sources/   # 5 source files (A–E)
└── *.json                   # Output schemas
docs/            # TODO.md, design notes (committed)
working/         # Run logs, scratch (gitignored)
scripts/         # ingest.py, start.sh
alembic/         # DB migrations
```

## Notes
- All prompts are in `src/prompts.py` — edit there to tune LLM behaviour
- HackerNews search uses Algolia's public API — no key required
- DB migrations run automatically on API container start
- Never commit `.env`
