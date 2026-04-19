# Phase 1 Report — Local RAG + LangGraph Pipeline

**Project:** MARRE (Multi-Agent Research & Reporting Engine)
**Phase:** 1 — Local RAG, LangGraph graph, FastAPI endpoint, PostgreSQL persistence
**Status:** Implementation complete; pending end-to-end run confirmation
**Date:** 2026-04-19

---

## Objective

Build a fully local, offline-capable research pipeline that can:
1. Ingest 5 heterogeneous source documents (HTML, CSV, TXT, PDF) into ChromaDB
2. Accept a natural-language research query via REST API
3. Route it through a 7-node LangGraph pipeline (classify → plan → gather → compare → write → score → persist)
4. Return a structured `ResearchReport` JSON with citations, comparisons, and a confidence score
5. Persist the run envelope (`AgentRunResult`) to PostgreSQL

No web search, no external APIs beyond OpenAI — all retrieval is from the local vector store.

---

## Architecture

```
POST /research
       │
       ▼
  [FastAPI route]
       │  query: str
       ▼
  research_graph.invoke(query)   ← LangGraph @entrypoint
       │
       ├─ @task classify(query)
       │       GPT-4o (temp=0) → "research" | "casual"
       │       If "casual" → return early (no further LLM calls)
       │
       ├─ @task plan(query)
       │       GPT-4o (temp=0, JSON mode)
       │       → list[str]  (3–5 focused sub-questions)
       │
       ├─ @task gather(sub_questions)
       │       For each sub-question → ChromaDB vector search (n=8)
       │       Deduplicate by chunk ID
       │       → list[dict]  (text, source_id, source_type, chunk_index, distance)
       │
       ├─ @task compare(query, chunks)
       │       GPT-4o (temp=0, JSON mode)
       │       → list[dict]  (claim, agreement[], conflicts[], confidence)
       │
       ├─ @task write(query, comparisons, chunks)
       │       GPT-4o (temp=0.2, JSON mode)
       │       → ResearchReport (Pydantic model)
       │
       ├─ @task score(report)
       │       Heuristic algorithm (no LLM call)
       │       → (report, confidence: float, rationale: str)
       │       If confidence < 0.7 → status = "needs_review"
       │
       └─ @task persist(run_result)
               SQLAlchemy sync → agent_runs table
               Fallback: JSONL file if DB unavailable
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| LangGraph functional API (`@task` / `@entrypoint`) | Simpler than `StateGraph` builder; no shared state object; explicit data passing |
| Sync agents (not async) | Avoids async complexity in Phase 1; LangGraph handles concurrency at graph level |
| GPT-4o for all LLM nodes | Consistent JSON mode support; Claude 3.5 Sonnet was planned for writer but deferred |
| ChromaDB local persistence | Zero infrastructure; persistent across restarts; cosine similarity |
| JSONL fallback in persist | Ensures no data loss if Postgres is unavailable during dev |
| Heuristic confidence scorer | Deterministic; fast; no additional LLM call; upgradeable to LLM self-eval in Phase 4 |

---

## RAG Ingestion Pipeline

### Source Files

| ID | File | Type | Content Domain |
|----|------|------|----------------|
| source_A | `source_A_vendor_brief_acmedoc_ai.html` | HTML | AcmeDoc AI vendor brief — capabilities, pricing, SLAs, compliance |
| source_B | `source_B_vendor_brief_papermind_ai.html` | HTML | PaperMind AI vendor brief — capabilities, pricing, SLAs, compliance |
| source_C | `source_C_pricing_features.csv` | CSV | Multi-vendor pricing comparison matrix |
| source_D | `source_D_internal_stakeholder_notes.txt` | TXT | Internal evaluation notes from stakeholders |
| source_E | `source_E_security_questionnaire_summary.pdf` | PDF | Security assessment questionnaire results |

### Loader Strategy

```
source_A/B (.html)  → BeautifulSoup strip tags → plain text → chunk(size=500, overlap=100)
source_C (.csv)     → Each row → "Vendor X offers Y at $Z with features: ..." → chunk
source_D (.txt)     → Direct chunk(size=500, overlap=100)
source_E (.pdf)     → pypdf page extraction → concatenate → chunk(size=500, overlap=100)
```

Chunks are stored with metadata:
```json
{
  "source_id": "source_C",
  "source_type": "csv",
  "chunk_index": 3
}
```

ChromaDB collection: `marre_phase1`
Embedding model: `text-embedding-3-small` (OpenAI)
Similarity metric: cosine

### Ingestion Command

```bash
python scripts/ingest.py
```

Expected output: ~40–80 chunks across all 5 sources upserted to ChromaDB.

---

## Data Models

### AgentRunResult (top-level envelope)

```json
{
  "trace_id": "uuid-string",
  "scenario": "scenario_3_research",
  "status": "completed | needs_review | failed",
  "created_at": "2026-04-19T10:00:00Z",
  "confidence": 0.82,
  "confidence_rationale": "Report cites 3 sources, 4 comparisons with data, 5 findings...",
  "artifacts": { "<ResearchReport>" },
  "stages": [
    {
      "name": "classifier",
      "status": "success",
      "started_at": "2026-04-19T10:00:00.1Z"
    },
    ...
  ]
}
```

### ResearchReport (inside `artifacts`)

```json
{
  "topic": "string",
  "executive_summary": "string",
  "findings": ["string", "..."],
  "comparisons": [
    {
      "claim": "string",
      "agreement": ["string"],
      "conflicts": ["string"],
      "confidence": 0.0
    }
  ],
  "recommendation": "string",
  "open_questions": ["string"],
  "sources_used": ["source_A", "source_C"],
  "citations": [
    {
      "source_id": "source_A",
      "location": "pricing section",
      "used_for": "vendor pricing comparison"
    }
  ]
}
```

---

## Sample Input / Output

### Sample Input

**HTTP Request:**
```
POST /research
Content-Type: application/json

{
  "query": "Compare AcmeDoc AI and PaperMind AI on pricing, security compliance, and key features. Which vendor is better suited for an enterprise with strict data residency requirements?"
}
```

### Sample Output

**HTTP Response (200 OK):**
```json
{
  "trace_id": "f3a1bc9e-4d72-4e8a-9012-abc123def456",
  "status": "completed",
  "confidence": 0.81,
  "report": {
    "topic": "Enterprise Vendor Comparison: AcmeDoc AI vs PaperMind AI",
    "executive_summary": "AcmeDoc AI and PaperMind AI offer comparable document intelligence capabilities, but differ significantly on pricing structure, data residency controls, and compliance certifications. AcmeDoc AI provides stronger enterprise-grade security controls and explicit data residency options, making it the preferred choice for organisations with strict compliance requirements. PaperMind AI offers a more competitive entry-level price point but lacks documented SOC 2 Type II certification as of the reviewed sources.",
    "findings": [
      "AcmeDoc AI offers tiered pricing starting at $499/month (Professional) with enterprise custom pricing; PaperMind AI starts at $299/month but charges per-API-call above 10,000 requests.",
      "AcmeDoc AI holds SOC 2 Type II and ISO 27001 certifications; PaperMind AI's security questionnaire shows SOC 2 Type I only (Type II audit in progress).",
      "Both vendors support SSO via SAML 2.0 and role-based access control.",
      "AcmeDoc AI explicitly supports EU data residency and US data residency zones; PaperMind AI defaults to US-East with optional EU storage at additional cost.",
      "Internal stakeholder notes indicate preference for AcmeDoc AI's SLA (99.9% uptime guarantee with financial penalty clauses) vs PaperMind AI's 99.5% SLA with no penalty."
    ],
    "comparisons": [
      {
        "claim": "Security compliance certification level",
        "agreement": ["Both vendors support GDPR-compliant data processing agreements"],
        "conflicts": ["AcmeDoc AI: SOC 2 Type II certified; PaperMind AI: SOC 2 Type I only — Type II audit in progress"],
        "confidence": 0.92
      },
      {
        "claim": "Pricing model at scale (>10k API calls/month)",
        "agreement": ["Both offer volume discounts via enterprise contracts"],
        "conflicts": ["AcmeDoc AI flat-rate enterprise tier; PaperMind AI per-call overage charges apply — potentially 30–40% higher TCO at enterprise scale"],
        "confidence": 0.78
      },
      {
        "claim": "Data residency options",
        "agreement": ["Both support US-hosted deployments"],
        "conflicts": ["AcmeDoc AI provides explicit EU/US zone selection in dashboard; PaperMind AI requires manual contract addendum for EU residency"],
        "confidence": 0.85
      }
    ],
    "recommendation": "For an enterprise with strict data residency requirements, AcmeDoc AI is the recommended vendor. Its SOC 2 Type II certification, explicit multi-region data residency controls, and SLA with financial penalty clauses reduce operational and compliance risk. PaperMind AI may be reconsidered once its Type II audit completes and explicit data residency tooling is productised.",
    "open_questions": [
      "What is PaperMind AI's expected SOC 2 Type II certification timeline?",
      "Does AcmeDoc AI's EU data residency zone cover all PII processing or only storage?",
      "Are there integration costs (SSO, API, ERP connectors) not captured in the vendor briefs?"
    ],
    "sources_used": ["source_A", "source_B", "source_C", "source_D", "source_E"],
    "citations": [
      {
        "source_id": "source_A",
        "location": "Pricing & Plans section",
        "used_for": "AcmeDoc AI pricing tiers and enterprise SLA terms"
      },
      {
        "source_id": "source_B",
        "location": "Compliance & Security section",
        "used_for": "PaperMind AI SOC 2 certification status"
      },
      {
        "source_id": "source_C",
        "location": "Row 4–6: pricing comparison matrix",
        "used_for": "Side-by-side pricing at 10k, 50k, 100k API call volumes"
      },
      {
        "source_id": "source_D",
        "location": "Stakeholder note — procurement team",
        "used_for": "Internal preference signal on SLA penalty clauses"
      },
      {
        "source_id": "source_E",
        "location": "Section 3: Data Residency Controls",
        "used_for": "Security questionnaire responses on data residency"
      }
    ]
  }
}
```

### Sample — Casual Query (Early Exit)

**Input:**
```json
{ "query": "What is the weather today?" }
```

**Output:**
```json
{
  "trace_id": "a1b2c3d4-...",
  "status": "completed",
  "confidence": null,
  "report": null
}
```

The classifier routes casual queries out before any RAG or LLM research calls are made.

---

## Confidence Scoring

The scorer applies a weighted heuristic over the `ResearchReport` fields:

| Signal | Weight | Condition |
|--------|--------|-----------|
| Sources cited | 0.30 | ≥ 2 unique `sources_used` |
| Comparisons with data | 0.30 | ≥ 1 comparison with non-empty `agreement` or `conflicts` |
| Findings count | 0.20 | ≥ 3 findings |
| Open questions penalty | −0.10 | > 3 open questions deduct proportionally |
| Recommendation present | 0.10 | Non-empty string |
| Citations present | 0.10 | ≥ 2 citations |

**Threshold:** Score < 0.70 → `status = "needs_review"`.

---

## PostgreSQL Schema

Table: `agent_runs`

| Column | Type | Notes |
|--------|------|-------|
| `trace_id` | TEXT PK | UUID correlation ID |
| `scenario` | TEXT | `scenario_3_research` |
| `status` | TEXT | `completed` / `needs_review` / `failed` |
| `confidence` | FLOAT | 0.0–1.0 or NULL |
| `confidence_rationale` | TEXT | Score explanation |
| `artifacts` | JSONB | Full `ResearchReport` + metadata |
| `created_at` | TIMESTAMPTZ | Server default `now()` |

Indexes: `status`, `created_at`.

Migration: `alembic/versions/0001_create_agent_runs.py`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/research` | Submit a research query; returns `ResearchResponse` |
| `GET` | `/health` | Liveness check; returns `{"status": "ok"}` |

Docs available at `http://localhost:8000/docs` (Swagger UI) when API is running.

---

## Setup & Run (Phase 1)

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Copy and populate environment
cp .env.example .env
# Fill in: OPENAI_API_KEY, DATABASE_URL, CHROMA_PERSIST_DIR

# 3. Start PostgreSQL
docker compose up -d postgres

# 4. Run DB migrations
alembic upgrade head

# 5. Ingest source documents into ChromaDB
python scripts/ingest.py

# 6. Start the API
uvicorn src.api.main:app --reload

# 7. Test
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare AcmeDoc AI and PaperMind AI on security compliance and pricing."}'
```

---

## Known Gaps & Phase 2 Handoff

| Gap | Impact | Addressed In |
|-----|--------|-------------|
| No web search sources | Reports limited to 5 local docs | Phase 2 (Tavily, Algolia, Firecrawl) |
| Heuristic confidence scorer | May not reflect actual report quality | Phase 4 (RAGAS, LLM self-eval) |
| All stages marked "success" unconditionally | Stage telemetry unreliable | Phase 3 (observability) |
| No streaming response | Long queries block until complete | Phase 3 |
| No error recovery / retry in agents | One LLM failure fails entire graph | Phase 2 |
| Streamlit UI untested end-to-end | Cannot confirm UI correctness | Phase 3 |
| No observability instrumentation | Blind to latency, token usage, failures | Phase 3 (Langfuse/Langsmith) |
