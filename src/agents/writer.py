import json
import os
from openai import OpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai

from src.prompts import WRITER_SYSTEM, WRITER_USER
from src.schemas.llm import ChunkContext, LLMMessage, WriterRequest, WriterResponse
from src.schemas.report import Comparison, ResearchReport

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = wrap_openai(OpenAI(api_key=os.environ["OPENAI_API_KEY"]))
    return _client


def _format_chunks(chunks: list[dict]) -> tuple[str, str]:
    """Returns (numbered context text, source index string)."""
    lines = []
    index_lines = []
    for i, c in enumerate(chunks, 1):
        collection = c.get("collection", "")
        if collection == "marre_hn":
            label = f"HackerNews — {c.get('title', '')} ({c.get('url', '')})"
        else:
            label = f"{c['source_id']} ({c.get('source_type', '')})"
        lines.append(f"[SOURCE-{i}] {label}\n{c['text']}")
        index_lines.append(f"  SOURCE-{i}: {label}")
    return "\n\n".join(lines), "\n".join(index_lines)


@traceable(name="writer", run_type="llm")
def write(query: str, comparisons: list[dict], chunks: list[dict]) -> ResearchReport:
    sources_used = sorted({c["source_id"] for c in chunks})
    context, source_index = _format_chunks(chunks)
    comparisons_text = json.dumps(comparisons, indent=2)

    chunk_contexts = [
        ChunkContext(
            source_id=c["source_id"],
            source_type=c.get("source_type", ""),
            collection=c.get("collection", ""),
            text=c["text"],
            title=c.get("title", ""),
            url=c.get("url", ""),
        )
        for c in chunks
    ]
    comparison_models = [Comparison(**c) for c in comparisons if isinstance(c, dict)]
    messages = [
        LLMMessage(role="system", content=WRITER_SYSTEM),
        LLMMessage(
            role="user",
            content=WRITER_USER.format(
                query=query,
                context=context,
                source_index=source_index,
                comparisons_text=comparisons_text,
                sources_used=sources_used,
            ),
        ),
    ]
    request = WriterRequest(
        query=query,
        chunks=chunk_contexts,
        comparisons=comparison_models,
        sources_used=sources_used,
        messages=messages,
    )

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[m.model_dump() for m in request.messages],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    raw = json.loads(response.choices[0].message.content)
    raw.setdefault("sources_used", sources_used)

    # Fallback: if LLM returned empty comparisons, inject comparator results
    if not raw.get("comparisons") and comparison_models:
        raw["comparisons"] = [c.model_dump() for c in comparison_models]

    result = WriterResponse(report=ResearchReport(**raw))
    return result.report
