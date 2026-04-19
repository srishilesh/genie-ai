"""
HackerNews search via the public Algolia HN API (no key required).
Pipeline: search → date filter (6 months) → LLM relevance filter → chunks
"""
import json
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import httpx
from openai import OpenAI

from src.prompts import HN_FILTER_SYSTEM, HN_FILTER_USER
from src.schemas.llm import HNFilterRequest, HNFilterResponse, LLMMessage

_HN_API = "https://hn.algolia.com/api/v1/search"
_CUTOFF_MONTHS = 6
_client: OpenAI | None = None

load_dotenv()


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def _search(query: str, n: int = 20) -> list[dict]:
    resp = httpx.get(
        _HN_API,
        params={"query": query, "hitsPerPage": n, "tags": "story"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("hits", [])


def _filter_recent(hits: list[dict], months: int = _CUTOFF_MONTHS) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
    recent = []
    for h in hits:
        ts = h.get("created_at_i") or 0
        created = datetime.fromtimestamp(ts, tz=timezone.utc)
        if created >= cutoff:
            recent.append(h)
    return recent


def _filter_relevant(query: str, hits: list[dict]) -> list[dict]:
    if not hits:
        return []

    summaries = [
        f"{i}. {h.get('title', '')} — {(h.get('story_text') or h.get('url') or '')[:200]}"
        for i, h in enumerate(hits)
    ]
    summaries_text = "\n".join(summaries)

    messages = [
        LLMMessage(role="system", content=HN_FILTER_SYSTEM),
        LLMMessage(role="user", content=HN_FILTER_USER.format(query=query, summaries=summaries_text)),
    ]
    request = HNFilterRequest(query=query, summaries=summaries, messages=messages)

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[m.model_dump() for m in request.messages],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = json.loads(response.choices[0].message.content)
    indices_raw = raw if isinstance(raw, list) else next(iter(raw.values()), [])
    result = HNFilterResponse(indices=[i for i in indices_raw if isinstance(i, int) and i < len(hits)])
    return [hits[i] for i in result.indices]


def _to_chunks(hits: list[dict], chunk_offset: int = 0) -> list[dict]:
    chunks = []
    for i, h in enumerate(hits):
        title = h.get("title", "")
        url = h.get("url", "")
        text = h.get("story_text") or ""
        points = h.get("points", 0)
        num_comments = h.get("num_comments", 0)
        created = h.get("created_at", "")
        object_id = h.get("objectID", "")

        content = (
            f"HackerNews: {title}\n"
            f"URL: {url}\n"
            f"Posted: {created} | Points: {points} | Comments: {num_comments}\n"
            f"{text[:600]}"
        ).strip()

        chunks.append({
            "text": content,
            "source_id": "hackernews",
            "source_type": "community",
            "chunk_index": chunk_offset + i,
            "url": url,
            "title": title,
            "points": points,
            "num_comments": num_comments,
            "created_at": created,
            "hn_id": object_id,
        })
    return chunks


def get_hn_chunks(
    query: str,
    n_search: int = 20,
    filter_recent: bool = False,
    filter_relevant: bool = False,
) -> list[dict]:
    hits = _search(query, n=n_search)
    if filter_recent:
        hits = _filter_recent(hits)
    if filter_relevant:
        hits = _filter_relevant(query, hits)
    return _to_chunks(hits)
