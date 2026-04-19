from __future__ import annotations

import os

import chromadb

from src.rag.embeddings import embed

COLLECTION_NAME = "marre_phase1"

_client = None
_collection = None


def _get_client():
    global _client
    if _client is None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_store")
        _client = chromadb.PersistentClient(path=persist_dir)
    return _client


def get_collection():
    global _collection
    if _collection is None:
        _collection = _get_client().get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def ingest_documents(chunks: list[dict]) -> None:
    collection = get_collection()
    batch_size = 100

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        embeddings = embed(texts)
        ids = [f"{c['source_id']}_chunk_{c['chunk_index']}" for c in batch]
        metadatas = [
            {
                "source_id": c["source_id"],
                "source_type": c["source_type"],
                "chunk_index": c["chunk_index"],
            }
            for c in batch
        ]
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
