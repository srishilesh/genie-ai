# Ideas & Brainstorming — Genie AI (MARRE)

## Architecture Considerations

### Confidence Scoring
- Could use a separate LLM call to evaluate the writer output against source chunks
- Alternative: compute cosine similarity between report claims and retrieved chunks as a proxy score
- Or: ask the LLM to self-rate with chain-of-thought and parse the score

### Conflict Detection
- Define "objective discrepancy" strictly: numeric fields (price, uptime %) are easy; qualitative claims need careful prompting
- Consider structured extraction first (extract claims as JSON), then compare programmatically

### Graph State Design
- State should carry: raw_query, classification, plan, retrieved_chunks, comparisons, report_draft, confidence, run_id
- Use LangGraph's functional API — each @task returns its slice of state

### CSV Conversion Strategy (source_C)
- Template: "Vendor {name} offers {plan} at ${price}/year with features: {features}. Uptime SLA: {uptime}%."
- Embed each row as a separate document with row metadata

## Future Ideas
- Streaming SSE responses from FastAPI for long research runs
- Multi-query retrieval: generate 3 query variants, union results, deduplicate
- Hybrid search: combine BM25 + semantic search in ChromaDB (once supported)
- Cache layer: Redis for repeated queries
