from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.rag.client import ingest_hn_chunks
from src.rag.retriever import retrieve, COLLECTION_HN
from src.tools.hackernews import get_hn_chunks, _search, _filter_recent, _filter_relevant

router = APIRouter(prefix="/hackernews", tags=["hackernews"])


class HNSearchResult(BaseModel):
    title: str
    url: str
    points: int
    num_comments: int
    created_at: str
    hn_id: str
    story_text: str | None = None


class HNIndexResponse(BaseModel):
    indexed: int
    chunks: list[dict]


class HNRetrieveResponse(BaseModel):
    query: str
    results: list[dict]
    avg_distance: float | None = None


@router.get("/search", response_model=list[HNSearchResult])
def search_hackernews(
    query: str = Query(..., min_length=1),
    n: int = Query(20, ge=1, le=50),
    filter_recent: bool = Query(False),
    filter_relevant: bool = Query(False),
) -> list[HNSearchResult]:
    """Search HackerNews via Algolia. Optionally filter by recency and LLM relevance."""
    hits = _search(query, n=n)
    if filter_recent:
        hits = _filter_recent(hits)
    if filter_relevant and hits:
        hits = _filter_relevant(query, hits)

    return [
        HNSearchResult(
            title=h.get("title", ""),
            url=h.get("url", ""),
            points=h.get("points", 0),
            num_comments=h.get("num_comments", 0),
            created_at=h.get("created_at", ""),
            hn_id=h.get("objectID", ""),
            story_text=(h.get("story_text") or "")[:500] or None,
        )
        for h in hits
    ]


@router.post("/index", response_model=HNIndexResponse)
def index_hackernews(
    query: str = Query(..., min_length=1),
    n_search: int = Query(20, ge=1, le=50),
) -> HNIndexResponse:
    """Search HN, filter, and index results into the HN ChromaDB collection."""
    chunks = get_hn_chunks(query, n_search=n_search)
    if not chunks:
        return HNIndexResponse(indexed=0, chunks=[])
    indexed = ingest_hn_chunks(chunks)
    return HNIndexResponse(indexed=indexed, chunks=chunks)


@router.get("/retrieve", response_model=HNRetrieveResponse)
def retrieve_hackernews(
    query: str = Query(..., min_length=1),
    n_results: int = Query(8, ge=1, le=20),
) -> HNRetrieveResponse:
    """Retrieve indexed HN chunks from ChromaDB for a query."""
    results = retrieve(query, n_results=n_results, collection_name=COLLECTION_HN)
    avg_dist = (
        sum(r["distance"] for r in results) / len(results) if results else None
    )
    return HNRetrieveResponse(query=query, results=results, avg_distance=avg_dist)
