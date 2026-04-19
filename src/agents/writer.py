import json
import os
from openai import OpenAI

from src.schemas.report import ResearchReport

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def _format_comparisons(comparisons: list[dict]) -> str:
    return json.dumps(comparisons, indent=2)


def _format_chunks(chunks: list[dict]) -> str:
    return "\n\n".join(f"[{c['source_id']}] {c['text']}" for c in chunks)


def write(query: str, comparisons: list[dict], chunks: list[dict]) -> ResearchReport:
    sources_used = sorted({c["source_id"] for c in chunks})
    context = _format_chunks(chunks)
    comparisons_text = _format_comparisons(comparisons)

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior research analyst producing a structured research report in JSON.\n\n"
                    "Reply ONLY with a JSON object matching this schema exactly:\n"
                    "{\n"
                    '  "topic": string,\n'
                    '  "executive_summary": string,\n'
                    '  "findings": [string, ...],\n'
                    '  "comparisons": [{"claim": string, "agreement": [string], "conflicts": [string], "confidence": number}],\n'
                    '  "recommendation": string,\n'
                    '  "open_questions": [string, ...],\n'
                    '  "sources_used": [string, ...],\n'
                    '  "citations": [{"source_id": string, "location": string, "used_for": string}]\n'
                    "}\n\n"
                    "Base every claim on the provided source excerpts only. Be factual and concise."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research query: {query}\n\n"
                    f"Source excerpts:\n{context}\n\n"
                    f"Comparison analysis:\n{comparisons_text}\n\n"
                    f"Sources available: {sources_used}"
                ),
            },
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    raw = json.loads(response.choices[0].message.content)
    raw.setdefault("sources_used", sources_used)
    return ResearchReport(**raw)
