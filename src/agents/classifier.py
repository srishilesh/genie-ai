import os
from openai import OpenAI

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def classify(query: str) -> str:
    """Return one of: casual | local_research | hn_research."""
    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify the user query into exactly one of these three categories:\n"
                    "- 'casual': small talk, greetings, or off-topic queries\n"
                    "- 'local_research': requires deep factual/technical research from structured "
                    "local sources (whitepapers, documentation, reports, CSV data)\n"
                    "- 'hn_research': asks about community opinions, trends, recent online discussions, "
                    "what people are saying, or requires live web/community data\n\n"
                    "Reply with exactly one word from the list above."
                ),
            },
            {"role": "user", "content": query},
        ],
        temperature=0,
        max_tokens=10,
    )
    label = response.choices[0].message.content.strip().lower()
    if label in ("casual", "local_research", "hn_research"):
        return label
    return "casual" if "casual" in label else "local_research"
