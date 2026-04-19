import re

from fastapi import HTTPException

_MIN_MEANINGFUL_CHARS = 5


def validate_query(query: str) -> str:
    """
    Strip whitespace, remove special characters, then enforce min length.
    Returns the cleaned query for use in downstream calls.
    Raises HTTP 422 if the query is too short to be meaningful.
    """
    stripped = query.strip()
    meaningful = re.sub(r"[^a-zA-Z0-9 ]", "", stripped)
    meaningful = meaningful.strip()

    if len(meaningful) < _MIN_MEANINGFUL_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"Query must contain at least {_MIN_MEANINGFUL_CHARS} meaningful characters (letters/digits). Got: {len(meaningful)!r}",
        )

    return stripped  # return original (with punctuation) for LLM; meaningful check was just for length
