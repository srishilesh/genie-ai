# TODO — Genie AI (MARRE)

## Phase 1 — ✅ Complete
- [x] Dependencies, Docker Compose, Dockerfile
- [x] RAG ingestion — HTML, CSV, TXT, PDF → ChromaDB (`marre_phase1`)
- [x] Embeddings — OpenAI `text-embedding-3-small`
- [x] PostgreSQL — `agent_runs` table, Alembic auto-migration on startup
- [x] Pydantic schemas — `ResearchReport`, LLM request/response schemas
- [x] LangGraph graph — planner → gatherer → comparator → writer → scorer → persist
- [x] FastAPI — `/health`, `POST /research`, `POST /research/stream` (SSE), `GET /runs/recent`
- [x] Streamlit UI — live pipeline trace, sidebar with recent runs

---

## Phase 2 — ✅ Complete

### HackerNews / Algolia
- [x] `src/tools/hackernews.py` — Algolia HN API (no key needed)
- [x] Live fetch + index into `marre_hn` ChromaDB collection on every query
- [x] Retry: up to 3 attempts with LLM-generated query variations on 0 results
- [x] Source selection: local vs HN by avg cosine distance comparison
- [x] Sub-questions used for retrieval from both collections
- [x] `/hackernews/search`, `/hackernews/index`, `/hackernews/retrieve` endpoints

### Prompts & Schemas
- [x] All LLM prompts centralised in `src/prompts.py`
- [x] Typed request/response schemas for every LLM call in `src/schemas/llm.py`

### Confidence Scoring
- [x] LLM judge (GPT-4o) — query relevance, factual grounding, coverage
- [x] Composite score: 40% structural + 60% LLM judge
- [x] Confidence retry: replan with focused sub-questions → 1 retry if < 0.7

### Writer
- [x] Numbered source excerpts `[SOURCE-N]` with source index
- [x] Comparisons field explicitly populated from comparator analysis
- [x] Fallback: inject comparator results if LLM returns empty comparisons

---

## Phase 3 — ✅ Complete

### LangSmith Observability
- [x] All agent nodes decorated with `@traceable`
- [x] HN API search (`hn_api_search`), relevance filter, variation generator all traced
- [x] OpenAI clients wrapped with `wrap_openai` for token tracking
- [x] `research_pipeline` root trace with trace_id + query metadata

---

## Productionalization — 🔜 Next

### Reliability
- [ ] Tenacity retry wrapper on all LLM calls (backoff on rate limits)
- [ ] Per-node timeout with graceful degradation
- [ ] Extended health check: DB connectivity + ChromaDB status

### Security
- [ ] API key auth on all endpoints (`X-Api-Key` header)
- [ ] Rate limiting (`slowapi`)
- [ ] Max query length enforcement (currently 5-char min only)

### Observability
- [ ] Token usage tracked per LLM call and stored in DB
- [ ] Per-node latency logged to `agent_runs` JSONB column
- [ ] `GET /runs/{trace_id}` — full run detail endpoint

### Deployment
- [ ] `.dockerignore` to exclude `chroma_store/`, `working/`, `.env`
- [ ] Multi-stage Dockerfile (build → slim runtime)
- [ ] Environment validation on startup (fail fast if required keys missing)
- [ ] `docker compose` production profile with resource limits

---

## Phase 4 — Pending
- [ ] RAGAS evaluations — faithfulness, answer relevance, context recall
- [ ] Safety guardrails — prompt injection detection, output validation
- [ ] Tavily web search integration
- [ ] Firecrawl scraping integration

---

## Backlog

### Chunking
- [ ] Semantic chunking vs fixed-size — benchmark retrieval quality
- [ ] Per-source chunk size tuning (CSV smaller, PDF larger)

### Latency
- [ ] Parallelize sub-question retrieval with `asyncio.gather` in gatherer
- [ ] LRU cache for repeated embeddings

### PostgreSQL
- [ ] `run_logs` table — per-node timing + token counts
- [ ] `GET /runs/{trace_id}` — full trace retrieval endpoint
