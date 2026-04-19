# TODO — Genie AI (MARRE)

## Phase 1 — Active

### Setup
- [x] Add all dependencies to `pyproject.toml`
- [x] Docker Compose — Postgres + FastAPI (Dockerfile added)
- [ ] `pip install -e .` confirmed working end-to-end

### RAG — Ingestion
- [x] `src/rag/loaders.py` — HTML, CSV, TXT, PDF parsers
- [x] `src/rag/embeddings.py` — OpenAI `text-embedding-3-small` (lazy client)
- [x] `src/rag/client.py` — ChromaDB PersistentClient + `ingest_documents()`
- [x] `src/rag/retriever.py` — `retrieve()` with optional source filter
- [x] `scripts/ingest.py` — ingestion confirmed working (12 chunks)

### Database (`src/db/`)
- [x] `src/db/session.py` — sync SQLAlchemy engine + `save_run()`
- [x] `alembic/versions/0001_create_agent_runs.py` — `agent_runs` table migration
- [x] `psycopg2-binary` added to `pyproject.toml`
- [ ] `docker compose up -d postgres` + `alembic upgrade head` confirmed working

### Schemas (`src/schemas/`)
- [x] `src/schemas/report.py` — `ResearchReport` Pydantic model
- [x] `src/schemas/run.py` — `AgentRunResult` Pydantic model

### LangGraph Graph
- [x] `src/agents/classifier.py` — GPT-4o research vs casual
- [x] `src/agents/planner.py` — GPT-4o sub-question breakdown
- [x] `src/agents/gatherer.py` — RAG retrieval, deduplicated
- [x] `src/agents/comparator.py` — GPT-4o conflicts & agreements
- [x] `src/agents/writer.py` — GPT-4o ResearchReport JSON
- [x] `src/agents/scorer.py` — heuristic confidence score
- [x] `src/agents/persist.py` — DB save with JSONL fallback
- [x] `src/graph.py` — all nodes wired under `@entrypoint`

### FastAPI
- [x] `src/api/main.py` — app init, CORS, /health
- [x] `src/api/routes/research.py` — POST /research (sync invoke)

### Remaining before Phase 1 complete
- [ ] `pip install -e .` + `alembic upgrade head` confirmed end-to-end
- [ ] End-to-end test: `POST /research` with a real query returns valid ResearchReport
- [ ] Update README with final Phase 1 status

## Ideas & Improvements

### Chunking Optimization
- [ ] Benchmark current fixed-size chunking vs semantic chunking (e.g. `langchain` `SemanticChunker`)
- [ ] Per-source-type chunk strategies: smaller chunks for CSV rows, larger for PDF narrative
- [ ] Overlap tuning — experiment with 10–20% overlap to reduce context loss at boundaries
- [ ] Evaluate chunk quality via retrieval hit-rate on known queries

### Latency Improvements
- [ ] Parallelize `planner` sub-questions — run gatherer for each sub-question concurrently (`asyncio.gather`)
- [ ] Cache embeddings for repeated queries (in-memory LRU or Redis)
- [ ] Switch writer node to streaming mode and surface partial output to API caller
- [ ] Profile each graph node; identify and optimize the slowest stage

### Confidence Scoring Methods
- [ ] Extend beyond heuristics: use LLM self-evaluation (ask model to rate its own answer confidence)
- [ ] Cross-source agreement as a signal: higher agreement → higher confidence
- [ ] Citation coverage: penalize reports that cite fewer than N sources
- [ ] Explore `RAGAS` faithfulness + answer relevance metrics as inline confidence signals (Phase 4 integration)
- [ ] Track confidence distribution over time in PostgreSQL for drift detection

### PostgreSQL — Logging & Tracing
- [ ] Add `run_logs` table: per-node execution times, token counts, error messages
- [ ] Store raw LLM prompts + responses in a `llm_traces` table (opt-in via env flag)
- [ ] Add `trace_id` propagation through all agent nodes → correlate logs end-to-end
- [ ] Expose `/runs/{trace_id}` GET endpoint to retrieve full run trace from DB
- [ ] Add index on `agent_runs.created_at` and `agent_runs.status` for dashboard queries

## Phase 2 — Pending
- [ ] Tavily web search integration
- [ ] Algolia / HackerNews with 6-month LLM filter
- [ ] Firecrawl scraping

## Phase 3 — Pending
- [ ] Streamlit UI
- [ ] Langfuse or Langsmith observability

## Phase 4 — Pending
- [ ] RAGAS evaluations
- [ ] Safety guardrails
