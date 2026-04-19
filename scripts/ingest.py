"""
Loads all source documents and ingests them into the ChromaDB marre_phase1 collection.
Run once before starting the API: python scripts/ingest.py
"""
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env")

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.rag.client import ingest_documents
from src.rag.loaders import load_all_sources


def main() -> None:
    print("Loading source documents...")
    chunks = load_all_sources()

    counts = Counter(c["source_id"] for c in chunks)
    for source_id, count in sorted(counts.items()):
        print(f"  {source_id}: {count} chunks")
    print(f"  Total: {len(chunks)} chunks")

    print("\nIngesting into ChromaDB (marre_phase1)...")
    ingest_documents(chunks)
    print("Done.")


if __name__ == "__main__":
    main()
