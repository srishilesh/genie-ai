# Genie AI — MARRE (Multi-Agent Research & Reporting Engine)

Automates the **Gather → Compare → Report** workflow using LangGraph, FastAPI, ChromaDB, and PostgreSQL.

## Architecture

```
POST /research
      │
      ▼
  LangGraph
  ┌─────────────────────────────────────────┐
  │  classifier → planner → source_gatherer │
  │      → comparator → writer              │
  │      → confidence_scorer → persist      │
  └─────────────────────────────────────────┘
      │
      ▼
  ResearchReport (JSON)
```

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph (functional API) |
| API | FastAPI + Uvicorn |
| Vector Store | ChromaDB (local) |
| Database | PostgreSQL 16 (Docker) |
| LLMs | GPT-4o (primary), Claude 3.5 Sonnet (writer) |
| Embeddings | OpenAI `text-embedding-3-small` |

## Quick Start

### 1. Prerequisites
- Python 3.11+
- Docker (for PostgreSQL)

### 2. Install dependencies
```bash
pip install -e .
```

### 3. Configure environment
```bash
cp .env.example .env
# Fill in OPENAI_API_KEY, ANTHROPIC_API_KEY
```

### 4. Start PostgreSQL
```bash
docker compose up -d postgres
```

### 5. Run DB migrations
```bash
alembic upgrade head
```

### 6. Ingest source documents into ChromaDB
```bash
python scripts/ingest.py
```

### 7. Start the API
```bash
uvicorn src.api.main:app --reload
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## API

### `POST /research`
Run the full research pipeline on a query.

**Request:**
```json
{ "query": "Compare AcmeDoc AI and PaperMind AI for enterprise document processing" }
```

**Response:** `ResearchReport` JSON matching `data/scenario3_research_report_schema.json`

### `GET /health`
Returns `{ "status": "ok" }`.

## Project Structure

```
src/
├── agents/      # LangGraph @task nodes
├── api/         # FastAPI app and routes
├── db/          # SQLAlchemy models + Alembic
├── rag/         # ChromaDB ingestion & retrieval
├── schemas/     # Pydantic models
└── graph.py     # LangGraph @entrypoint
data/
├── research_pack/sources/   # Source files A–E
└── *.json                   # Output schemas
docs/            # TODOs, ideas, design notes
working/         # Session logs (gitignored)
```

## Phases

| Phase | Status | Scope |
|---|---|---|
| 1 | **Active** | Local RAG, graph logic, FastAPI, PostgreSQL |
| 2 | Pending | Tavily, Algolia/HackerNews, Firecrawl |
| 3 | Pending | Streamlit UI, Langfuse/Langsmith |
| 4 | Pending | RAGAS evals, safety guardrails |

## Development Notes
- Working memory files go in `working/` (gitignored)
- Design docs, TODOs, ideas go in `docs/` (committed)
- Never commit `.env`
