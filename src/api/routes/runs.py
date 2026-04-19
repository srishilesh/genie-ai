import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/runs", tags=["runs"])

_JSONL = Path("working/runs.jsonl")


def _from_jsonl(n: int) -> list[dict]:
    if not _JSONL.exists():
        return []
    lines = _JSONL.read_text().strip().splitlines()
    runs = []
    for line in reversed(lines):
        try:
            runs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(runs) >= n:
            break
    return runs


def _from_db(n: int) -> list[dict]:
    from src.db.session import _get_engine
    from sqlalchemy import text
    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT trace_id, status, confidence, created_at, artifacts->>'report' as report FROM agent_runs ORDER BY created_at DESC LIMIT :n"),
            {"n": n},
        ).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/recent")
def recent_runs(n: int = 3) -> list[dict]:
    try:
        runs = _from_db(n)
        if runs:
            return runs
    except Exception:
        pass
    runs = _from_jsonl(n)
    return [
        {
            "trace_id": r.get("trace_id"),
            "status": r.get("status"),
            "confidence": r.get("confidence"),
            "created_at": r.get("created_at"),
            "query": r.get("query", "—"),
        }
        for r in runs
    ]
