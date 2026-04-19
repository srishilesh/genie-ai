import json
import os
from openai import OpenAI

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def plan(query: str) -> list[str]:
    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You break a research query into 3–5 focused sub-questions that, "
                    "together, fully answer the original query. "
                    "Reply with a JSON array of strings and nothing else."
                ),
            },
            {"role": "user", "content": query},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    return next(iter(parsed.values()))
