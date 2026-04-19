import logging

from langsmith import traceable

from src.rag.client import ingest_hn_chunks
from src.rag.retriever import retrieve, COLLECTION_LOCAL, COLLECTION_HN
from src.tools.hackernews import get_hn_chunks

log = logging.getLogger(__name__)

_QUICK_N = 5


def _avg_distance(chunks: list[dict]) -> float:
    return sum(c["distance"] for c in chunks) / len(chunks) if chunks else float("inf")


@traceable(name="classifier")
def classify(query: str) -> dict:
    """
    1. Local RAG → avg distance score
    2. HN API → index → retrieve → avg distance score
    3. Lower avg distance wins → local_research | hn_research

    Returns a dict with research_type + scoring details for stream visibility.
    """
    # ── 1. Local retrieval ────────────────────────────────────────────────────
    local_chunks = retrieve(query, n_results=_QUICK_N, collection_name=COLLECTION_LOCAL)
    local_avg = _avg_distance(local_chunks)
    log.info("Local avg_dist=%.4f", local_avg)

    # ── 2. HN: always fetch live, index, then retrieve ────────────────────────
    hn_avg = float("inf")
    hn_fetched = 0
    try:
        raw = get_hn_chunks(query)
        hn_fetched = len(raw)
        if raw:
            ingest_hn_chunks(raw)
            hn_chunks = retrieve(query, n_results=_QUICK_N, collection_name=COLLECTION_HN)
            hn_avg = _avg_distance(hn_chunks)
            log.info("HN fetched %d chunks, avg_dist=%.4f", hn_fetched, hn_avg)
        else:
            log.info("HN returned 0 results")
    except Exception as exc:
        log.warning("HN fetch failed: %s", exc)

    # ── 3. Pick winner ────────────────────────────────────────────────────────
    research_type = "local_research" if local_avg <= hn_avg else "hn_research"
    log.info("Selected: %s (local=%.4f, hn=%.4f)", research_type, local_avg, hn_avg)
    return {
        "research_type": research_type,
        "local_avg_distance": round(local_avg, 4),
        "hn_avg_distance": round(hn_avg, 4) if hn_avg != float("inf") else None,
        "hn_fetched": hn_fetched,
    }
