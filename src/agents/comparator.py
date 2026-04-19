import json
import os
from openai import OpenAI

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def _format_chunks(chunks: list[dict]) -> str:
    lines = []
    for c in chunks:
        lines.append(f"[{c['source_id']}] {c['text']}")
    return "\n\n".join(lines)


def compare(query: str, chunks: list[dict]) -> list[dict]:
    context = _format_chunks(chunks)
    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a research analyst. Given source excerpts, identify key claims relevant "
                    "to the research query. For each claim, list which sources agree and which conflict.\n\n"
                    "Reply ONLY with a JSON array where each item has:\n"
                    '  "claim": string (the topic or claim being compared)\n'
                    '  "agreement": array of strings (facts that sources agree on)\n'
                    '  "conflicts": array of strings (objective discrepancies between sources)\n'
                    '  "confidence": number 0.0–1.0 (how well-supported this claim is)\n\n'
                    "Focus on objective, factual discrepancies (numbers, dates, certifications, pricing)."
                ),
            },
            {
                "role": "user",
                "content": f"Research query: {query}\n\nSource excerpts:\n{context}",
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    return next(iter(parsed.values()))
