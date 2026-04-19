import logging

from src.rag.client import ingest_hn_chunks
from src.rag.retriever import retrieve, COLLECTION_LOCAL, COLLECTION_HN
from src.tools.hackernews import get_hn_chunks

log = logging.getLogger(__name__)


def gather(
    query: str,
    sub_questions: list[str],
    research_type: str = "local_research",
    n_per_question: int = 5,
) -> list[dict]:
    """
    research_type: 'local_research' → local ChromaDB only
                   'hn_research'    → HackerNews: fetch live, index, then retrieve
    """
    if research_type == "hn_research":
        try:
            raw = get_hn_chunks(query)
            indexed = ingest_hn_chunks(raw)
            log.info("HN: indexed %d chunks", indexed)
        except Exception as exc:
            log.warning("HN indexing failed: %s", exc)

        return retrieve(query, n_results=n_per_question * 2, collection_name=COLLECTION_HN)

    # default: local_research
    seen: set[str] = set()
    chunks: list[dict] = []
    for question in sub_questions:
        for chunk in retrieve(question, n_results=n_per_question, collection_name=COLLECTION_LOCAL):
            cid = f"{chunk['source_id']}_{chunk['chunk_index']}"
            if cid not in seen:
                seen.add(cid)
                chunks.append(chunk)
    return chunks
