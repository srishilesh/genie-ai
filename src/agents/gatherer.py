import logging

from langsmith import traceable

from src.rag.client import ingest_hn_chunks
from src.rag.retriever import retrieve, COLLECTION_LOCAL, COLLECTION_HN
from src.tools.hackernews import get_hn_chunks, get_query_variations

log = logging.getLogger(__name__)

_N_PER_QUESTION = 5


def _avg_distance(chunks: list[dict]) -> float:
    return sum(c["distance"] for c in chunks) / len(chunks) if chunks else float("inf")


def _retrieve_per_subquestion(sub_questions: list[str], n: int, collection: str) -> list[dict]:
    seen: set[str] = set()
    chunks: list[dict] = []
    for question in sub_questions:
        for chunk in retrieve(question, n_results=n, collection_name=collection):
            cid = f"{chunk['source_id']}_{chunk['chunk_index']}"
            if cid not in seen:
                seen.add(cid)
                chunks.append(chunk)
    return chunks


@traceable(name="gatherer")
def gather(query: str, sub_questions: list[str], n_per_question: int = _N_PER_QUESTION) -> dict:
    """
    1. Fetch HN live → index into marre_hn
    2. Retrieve per sub-question from both local and HN collections
    3. Compare avg distances → return chunks from the better source

    Returns dict with chunks + metadata for stream visibility.
    """
    # ── 1. HN: fetch live with up to 3 retries using query variations ─────────
    hn_fetched = 0
    hn_warning: str | None = None
    _MAX_HN_RETRIES = 3

    def _try_hn(q: str) -> list[dict]:
        raw = get_hn_chunks(q)
        if raw:
            ingest_hn_chunks(raw)
            log.info("HN: fetched and indexed %d chunks for query=%r", len(raw), q)
        return raw

    try:
        raw = _try_hn(query)
        hn_fetched = len(raw)

        if not raw:
            log.warning("HN: 0 results for original query — generating variations")
            variations = get_query_variations(query)
            for i, variation in enumerate(variations[:_MAX_HN_RETRIES], 1):
                log.info("HN retry %d/%d with variation=%r", i, _MAX_HN_RETRIES, variation)
                raw = _try_hn(variation)
                if raw:
                    hn_fetched = len(raw)
                    log.info("HN: found %d results on retry %d", hn_fetched, i)
                    break

        if not raw:
            hn_warning = (
                f"HackerNews returned 0 results after {_MAX_HN_RETRIES} retries with query variations. "
                "The topic may not be discussed on HN or the query may need rephrasing. "
                "Results are from local sources only — manual review recommended."
            )
    except Exception as exc:
        log.warning("HN fetch failed: %s", exc)
        hn_warning = f"HackerNews fetch failed ({exc}). Results are from local sources only — manual review recommended."

    # ── 2. Retrieve from both collections per sub-question ───────────────────
    local_chunks = _retrieve_per_subquestion(sub_questions, n_per_question, COLLECTION_LOCAL)
    hn_chunks = _retrieve_per_subquestion(sub_questions, n_per_question, COLLECTION_HN)

    local_avg = _avg_distance(local_chunks)
    hn_avg = _avg_distance(hn_chunks)

    log.info("Scores — local_avg=%.4f  hn_avg=%.4f", local_avg, hn_avg)

    # ── 3. Pick better source ─────────────────────────────────────────────────
    if local_avg <= hn_avg:
        selected, chunks = "local", local_chunks
    else:
        selected, chunks = "hn", hn_chunks

    log.info("Selected: %s", selected)

    return {
        "chunks": chunks,
        "selected_source": selected,
        "hn_fetched": hn_fetched,
        "hn_warning": hn_warning,
        "local_avg_distance": round(local_avg, 4),
        "hn_avg_distance": round(hn_avg, 4) if hn_avg != float("inf") else None,
    }
