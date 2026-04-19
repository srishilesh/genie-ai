from __future__ import annotations

import hashlib
import os

import chromadb

from src.rag.embeddings import embed

COLLECTION_LOCAL = "marre_phase1"
COLLECTION_HN = "marre_hn"

_client = None
_collections: dict[str, chromadb.Collection] = {}


def _get_client():
    global _client
    if _client is None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_store")
        _client = chromadb.PersistentClient(path=persist_dir)
    return _client


def get_collection(name: str = COLLECTION_LOCAL):
    if name not in _collections:
        _collections[name] = _get_client().get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collections[name]


def ingest_documents(chunks: list[dict]) -> None:
    collection = get_collection(COLLECTION_LOCAL)
    _upsert(collection, chunks, id_fn=lambda c: f"{c['source_id']}_chunk_{c['chunk_index']}")


def ingest_hn_chunks(chunks: list[dict]) -> int:
    """Embed and upsert HN chunks. Uses URL hash as ID for deduplication. Returns count upserted."""
    if not chunks:
        return 0
    collection = get_collection(COLLECTION_HN)

    def _id(c: dict) -> str:
        key = c.get("url") or c["text"][:120]
        return "hn_" + hashlib.md5(key.encode()).hexdigest()

    _upsert(collection, chunks, id_fn=_id)
    return len(chunks)


def _upsert(collection, chunks: list[dict], id_fn) -> None:
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        embeddings = embed(texts)
        ids = [id_fn(c) for c in batch]
        metadatas = [
            {
                "source_id": c.get("source_id", "hackernews"),
                "source_type": c.get("source_type", "community"),
                "chunk_index": c.get("chunk_index", i + j),
                "url": c.get("url", ""),
                "title": c.get("title", ""),
                "points": c.get("points", 0),
                "num_comments": c.get("num_comments", 0),
                "created_at": c.get("created_at", ""),
                "hn_id": c.get("hn_id", ""),
            }
            for j, c in enumerate(batch)
        ]
        collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
