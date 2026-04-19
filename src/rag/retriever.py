from src.rag.client import COLLECTION_HN, COLLECTION_LOCAL, get_collection
from src.rag.embeddings import embed


def retrieve(
    query: str,
    n_results: int = 8,
    source_filter: list[str] | None = None,
    collection_name: str = COLLECTION_LOCAL,
) -> list[dict]:
    collection = get_collection(collection_name)
    query_embedding = embed([query])[0]
    where = {"source_id": {"$in": source_filter}} if source_filter else None

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            where=where,
        )
    except Exception:
        return []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {
            "text": doc,
            "source_id": meta.get("source_id", "unknown"),
            "source_type": meta.get("source_type", "unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "url": meta.get("url", ""),
            "title": meta.get("title", ""),
            "points": meta.get("points", 0),
            "num_comments": meta.get("num_comments", 0),
            "created_at": meta.get("created_at", ""),
            "hn_id": meta.get("hn_id", ""),
            "collection": collection_name,
            "distance": dist,
        }
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]


def _avg_distance(chunks: list[dict]) -> float:
    if not chunks:
        return float("inf")
    return sum(c["distance"] for c in chunks) / len(chunks)


def retrieve_best(query: str, n_per_collection: int = 6) -> tuple[list[dict], str]:
    """Query both collections; return chunks from whichever has better avg relevance."""
    local = retrieve(query, n_results=n_per_collection, collection_name=COLLECTION_LOCAL)
    hn = retrieve(query, n_results=n_per_collection, collection_name=COLLECTION_HN)
    if _avg_distance(local) <= _avg_distance(hn):
        return local, COLLECTION_LOCAL
    return hn, COLLECTION_HN


def retrieve_all(query: str, n_per_collection: int = 6) -> list[dict]:
    """Search both local KB and HN collection, merge by relevance (distance)."""
    local = retrieve(query, n_results=n_per_collection, collection_name=COLLECTION_LOCAL)
    hn = retrieve(query, n_results=n_per_collection, collection_name=COLLECTION_HN)
    combined = local + hn
    combined.sort(key=lambda c: c["distance"])
    return combined
