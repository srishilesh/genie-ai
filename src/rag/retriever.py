from src.rag.client import get_collection
from src.rag.embeddings import embed


def retrieve(
    query: str,
    n_results: int = 8,
    source_filter: list[str] | None = None,
) -> list[dict]:
    collection = get_collection()
    query_embedding = embed([query])[0]

    where = {"source_id": {"$in": source_filter}} if source_filter else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {
            "text": doc,
            "source_id": meta["source_id"],
            "source_type": meta["source_type"],
            "chunk_index": meta["chunk_index"],
            "distance": dist,
        }
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]
