import json
import os
from openai import OpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai

from src.prompts import COMPARATOR_SYSTEM, COMPARATOR_USER
from src.schemas.llm import ChunkContext, ComparatorRequest, ComparatorResponse, LLMMessage
from src.schemas.report import Comparison

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = wrap_openai(OpenAI(api_key=os.environ["OPENAI_API_KEY"]))
    return _client


def _format_chunks(chunks: list[dict]) -> str:
    lines = []
    for i, c in enumerate(chunks):
        collection = c.get("collection", "")
        if collection == "marre_hn":
            title = c.get("title", "")
            url = c.get("url", "")
            uid = f"HN-{i+1}"
            header = f"[{uid}] HackerNews | {title} | {url}"
        else:
            uid = f"LOCAL-{i+1}"
            header = f"[{uid}] {c['source_id']} ({c.get('source_type', '')})"
        lines.append(f"{header}\n{c['text']}")
    return "\n\n".join(lines)


@traceable(name="comparator", run_type="llm")
def compare(query: str, chunks: list[dict]) -> list[dict]:
    context = _format_chunks(chunks)
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
    messages = [
        LLMMessage(role="system", content=COMPARATOR_SYSTEM),
        LLMMessage(role="user", content=COMPARATOR_USER.format(query=query, context=context)),
    ]
    request = ComparatorRequest(query=query, chunks=chunk_contexts, messages=messages)

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[m.model_dump() for m in request.messages],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = json.loads(response.choices[0].message.content)
    items = raw if isinstance(raw, list) else next(iter(raw.values()))
    result = ComparatorResponse(
        comparisons=[Comparison(**item) for item in items if isinstance(item, dict)]
    )
    return [c.model_dump() for c in result.comparisons]
