# CLAUDE.md — Genie AI (MARRE)

## Project
Multi-Agent Research & Reporting Engine (MARRE). Automates the Gather → Compare → Report workflow using LangGraph functional API, FastAPI, ChromaDB, and PostgreSQL.

## Directory Layout
```
genie-ai/
├── src/
│   ├── agents/          # LangGraph node functions (classifier, planner, gatherer, comparator, writer, scorer, persist)
│   ├── api/             # FastAPI app, routes, request/response models
│   ├── db/              # SQLAlchemy models + session factory
│   ├── rag/             # ChromaDB ingestion pipeline & retrieval helpers
│   ├── schemas/         # Pydantic models mirroring JSON schemas
│   └── graph.py         # LangGraph @entrypoint — wires all nodes
├── data/
│   ├── research_pack/sources/   # 5 source files (A–E)
│   ├── agent_run_result_schema.json
│   └── scenario3_research_report_schema.json
├── docs/                # TODOs, reports, ideas, brainstorming — commit these
├── working/             # Session logs, scratch files — gitignored
├── scripts/             # One-off helper scripts
├── .claude/
│   ├── settings.json    # Claude Code hooks config
│   └── hooks/           # Hook shell scripts
├── .env                 # Secret — never commit
├── .env.example         # Committed template
├── docker-compose.yml   # PostgreSQL local setup
├── pyproject.toml
└── CLAUDE.md
```

## Tech Stack
| Layer | Tool |
|---|---|
| Orchestration | LangGraph (functional API: `@task`, `@entrypoint`) |
| API | FastAPI |
| Vector Store | ChromaDB (local persistence at `./chroma_store`) |
| Database | PostgreSQL 16 via SQLAlchemy (async) |
| LLMs | OpenAI GPT-4o (primary), Claude 3.5 Sonnet (writer node) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Validation | Pydantic v2 |

## LangGraph Graph — Scenario 3 (Research)
All nodes use the functional API (`@task` decorated async functions composed under `@entrypoint`).

```
query_in
   │
   ▼
[classifier]  →  casual → return early
   │ research
   ▼
[planner]
   │
   ▼
[source_gatherer]   ← ChromaDB RAG across sources A–E
   │
   ▼
[comparator]        ← identify conflicts & agreements
   │
   ▼
[writer]            ← Claude 3.5 Sonnet → ResearchReport JSON
   │
   ▼
[confidence_scorer] ← score 0–1; if < 0.7 → status = needs_review
   │
   ▼
[persist]           ← save AgentRunResult to PostgreSQL
   │
   ▼
AgentRunResult (JSON response)
```

## Key Schemas
- `data/agent_run_result_schema.json` — top-level run envelope (trace_id, scenario, status, stages, artifacts)
- `data/scenario3_research_report_schema.json` — ResearchReport inside `artifacts`
- Status rules: `completed` | `needs_review` (confidence < 0.7) | `failed`

## RAG — Source Ingestion (Phase 1)
| File | Handling |
|---|---|
| source_A/B `.html` | BeautifulSoup → strip tags → chunk |
| source_C `.csv` | Each row → descriptive text string before embedding |
| source_D `.txt` | Chunk directly |
| source_E `.pdf` | pypdf → extract text → chunk |

Collection name: `marre_phase1`. Metadata: `source_id`, `source_type`, `chunk_index`.

## Environment Variables
See `.env.example`. Required for Phase 1:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `DATABASE_URL`
- `CHROMA_PERSIST_DIR`

## Local PostgreSQL
```bash
docker compose up -d postgres
```
Run Alembic migrations after models are defined:
```bash
alembic upgrade head
```

## Working Conventions
- **`working/`** — session logs, scratch, change logs. Gitignored. Claude hooks write here.
- **`docs/`** — committed. All TODOs (`docs/TODO.md`), design notes, phase reports, ideas go here.
- Never commit `.env`. Always update `.env.example` when adding new vars.
- No manual code runs — user handles `python`, `docker`, `alembic` commands.
- Do not add tests until explicitly requested.
- LangGraph: always use functional API (`@task` / `@entrypoint`), never `StateGraph` builder.
- Comments only for non-obvious WHY, not what.

## Phases
- **Phase 1 (active)**: Local RAG, graph logic, FastAPI endpoint, PostgreSQL persistence.
- **Phase 2**: Tavily (web search), Algolia (HackerNews, 6-month LLM filter), Firecrawl (scraping).
- **Phase 3**: Streamlit UI, Langfuse/Langsmith observability.
- **Phase 4**: RAGAS evaluations, safety guardrails.

## Claude Hooks
- `PostToolUse` on Write/Edit → `.claude/hooks/log_changes.sh` → appends to `working/session_changes.log`
- If a `.py` src file changes → appends reminder to `working/pending_doc_updates.md`
- Reminder surfaces to update `docs/TODO.md` and `README.md` when relevant

## Key Commands (run by user)
```bash
# Start Postgres
docker compose up -d postgres

# Install deps
pip install -e ".[dev]"

# Ingest sources into ChromaDB
python scripts/ingest.py

# Run API
uvicorn src.api.main:app --reload

# DB migrations
alembic upgrade head
```
