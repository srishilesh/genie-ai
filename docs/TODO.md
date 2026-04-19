# TODO — Genie AI (MARRE)

## Phase 1 — ✅ Complete

- [x] Dependencies, Docker Compose (Postgres + API + UI), Dockerfile
- [x] RAG ingestion — HTML, CSV, TXT, PDF → ChromaDB (`marre_phase1`, 12 chunks)
- [x] Embeddings — OpenAI `text-embedding-3-small` (lazy client)
- [x] PostgreSQL — `agent_runs` table, Alembic auto-migration on startup
- [x] Pydantic schemas — `ResearchReport`, `AgentRunResult`
- [x] LangGraph graph — 7 nodes: classifier → planner → gatherer → comparator → writer → scorer → persist
- [x] FastAPI — `/health`, `POST /research` (sync), `POST /research/stream` (SSE), `GET /runs/recent`
- [x] Streamlit UI — live pipeline trace, sidebar with API key + recent runs, click-to-load history

---

## Phase 2 — 🔄 Active

### Algolia / HackerNews ✅
- [x] `src/tools/hackernews.py` — public Algolia HN API (no key needed)
- [x] Date filter: discard items older than 6 months
- [x] LLM relevance filter: GPT-4o selects top 5 relevant results
- [x] Merged into `gatherer` node with `source_id: "hackernews"`, `source_type: "community"`
- [x] UI: RAG vs HN chunks shown separately in pipeline trace with clickable URLs

### Tavily (Web Search) — Parked
- [ ] `src/tools/tavily.py` — parked until after productionalization

### Firecrawl (Scraping) — Parked
- [ ] `src/tools/firecrawl.py` — parked until after productionalization

---

## Productionalization — 🔜 Next

### Reliability
- [ ] Retry logic on all LLM calls (tenacity — already in deps)
- [ ] Timeout per node with graceful degradation (skip HN if it times out)
- [ ] Health check endpoint extended: DB connectivity + ChromaDB status
- [ ] Structured logging (JSON log lines) via `python-json-logger`

### Security
- [ ] API key auth on all endpoints (`X-Api-Key` header, env-configured)
- [ ] Rate limiting (`slowapi`)
- [ ] Input sanitization — max query length, strip dangerous chars

### Observability
- [ ] Per-node timing logged to `agent_runs.stages` JSONB column
- [ ] Token usage tracked per LLM call and stored in DB
- [ ] `GET /runs/{trace_id}` — full run detail endpoint

### Deployment
- [ ] `.dockerignore` to exclude `chroma_store/`, `working/`, `.env`
- [ ] Multi-stage Dockerfile (build → slim runtime)
- [ ] `docker compose` production profile with resource limits
- [ ] Environment validation on startup (fail fast if required keys missing)

---

## Phase 3 — Pending
- [x] Streamlit UI (moved up, done in Phase 1)
- [ ] Langfuse or Langsmith observability — trace LLM calls per node
- [ ] Langfuse dashboard: token counts, latency per node, confidence trends

## Phase 4 — Pending
- [ ] RAGAS evaluations — faithfulness, answer relevance, context recall
- [ ] Safety guardrails — prompt injection detection, output validation

---

## Ideas & Improvements (Backlog)

### Chunking
- [ ] Semantic chunking vs fixed-size — benchmark retrieval hit-rate
- [ ] Per-source chunk size tuning (CSV smaller, PDF larger)

### Latency
- [ ] Parallelize gatherer sub-question retrieval with `asyncio.gather`
- [ ] LRU cache for repeated embeddings

### Confidence Scoring
- [ ] LLM self-evaluation as confidence signal
- [ ] RAGAS faithfulness metric as inline scorer (Phase 4)

### PostgreSQL
- [ ] `run_logs` table — per-node timing + token counts
- [ ] `GET /runs/{trace_id}` — full trace retrieval endpoint
