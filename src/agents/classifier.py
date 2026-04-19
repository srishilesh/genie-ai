import os
from openai import OpenAI

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def classify(query: str) -> str:
    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You classify user queries. Reply with exactly one word: "
                    "'research' if the query requires research, analysis, or comparison of information. "
                    "'casual' if it is small talk, greetings, or off-topic."
                ),
            },
            {"role": "user", "content": query},
        ],
        temperature=0,
        max_tokens=10,
    )
    label = response.choices[0].message.content.strip().lower()
    return "research" if "research" in label else "casual"
