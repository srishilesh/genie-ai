from src.rag.retriever import retrieve


def gather(sub_questions: list[str], n_per_question: int = 5) -> list[dict]:
    seen_ids: set[str] = set()
    chunks: list[dict] = []

    for question in sub_questions:
        for chunk in retrieve(question, n_results=n_per_question):
            chunk_id = f"{chunk['source_id']}_{chunk['chunk_index']}"
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                chunks.append(chunk)

    return chunks
