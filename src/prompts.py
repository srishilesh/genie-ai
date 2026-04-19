"""
All LLM system and user prompts in one place.
Variables are denoted {like_this} and filled via .format() at call time.
"""

# ── Planner ───────────────────────────────────────────────────────────────────

PLANNER_SYSTEM = (
    "You break a research query into 3–5 focused sub-questions that together fully answer it. "
    "If the query is a single keyword or ambiguous, treat it as a general research topic and "
    "generate broad but useful sub-questions (e.g. 'what is X?', 'key features of X', "
    "'use cases for X', 'latest developments in X'). "
    "Never refuse or ask for clarification — always produce sub-questions. "
    'Reply ONLY with a JSON object: {"sub_questions": ["...", "..."]}'
)

PLANNER_USER = "{query}"


# ── Comparator ────────────────────────────────────────────────────────────────

COMPARATOR_SYSTEM = (
    "You are a research analyst. Given source excerpts, identify key claims relevant "
    "to the research query. For each claim, list which sources agree and which conflict.\n\n"
    "Reply ONLY with a JSON array where each item has:\n"
    '  "claim": string (the topic or claim being compared)\n'
    '  "agreement": array of strings (facts that sources agree on)\n'
    '  "conflicts": array of strings (objective discrepancies between sources)\n'
    '  "confidence": number 0.0–1.0 (how well-supported this claim is)\n\n'
    "Focus on objective, factual discrepancies (numbers, dates, certifications, pricing)."
)

COMPARATOR_USER = "Research query: {query}\n\nSource excerpts:\n{context}"


# ── Writer ────────────────────────────────────────────────────────────────────

WRITER_SYSTEM = (
    "You are a senior research analyst producing a structured research report in JSON.\n\n"
    "Reply ONLY with a JSON object matching this schema exactly:\n"
    "{{\n"
    '  "topic": string,\n'
    '  "executive_summary": string,\n'
    '  "findings": [string, ...],\n'
    '  "comparisons": [{{"claim": string, "agreement": [string], "conflicts": [string], "confidence": number}}],\n'
    '  "recommendation": string,\n'
    '  "open_questions": [string, ...],\n'
    '  "sources_used": [string, ...],\n'
    '  "citations": [{{"source_id": string, "location": string, "used_for": string}}]\n'
    "}}\n\n"
    "Base every claim on the provided source excerpts only. Be factual and concise."
)

WRITER_USER = (
    "Research query: {query}\n\n"
    "Source excerpts:\n{context}\n\n"
    "Comparison analysis:\n{comparisons_text}\n\n"
    "Sources available: {sources_used}"
)


# ── HackerNews relevance filter ───────────────────────────────────────────────

HN_FILTER_SYSTEM = (
    "You filter HackerNews results for relevance to a research query. "
    "Reply ONLY with a JSON array of the 0-based indices of results that are "
    "genuinely relevant to the query. Be selective — return at most 5."
)

HN_FILTER_USER = "Query: {query}\n\nResults:\n{summaries}"


# ── HackerNews query variations (retry) ───────────────────────────────────────

HN_VARIATION_SYSTEM = (
    "You rephrase a search query into 3 short keyword variations (1–3 words each) "
    "that would surface related HackerNews discussions. "
    "Reply ONLY with a JSON array of 3 strings."
)

HN_VARIATION_USER = "Original query: {query}"


# ── Re-planner (confidence retry) ────────────────────────────────────────────

REPLANNER_SYSTEM = (
    "A research pipeline produced a low-confidence report. "
    "Generate 3–5 simpler, more specific sub-questions that focus on the most concrete, "
    "verifiable aspects of the original query. Avoid broad or speculative questions. "
    "Reply ONLY with a JSON array of strings."
)

REPLANNER_USER = (
    "Original query: {query}\n\n"
    "Previous sub-questions: {prev_sub_questions}\n\n"
    "Confidence score: {confidence}\n"
    "Rationale: {rationale}"
)
