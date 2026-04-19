"""
PostgreSQL persistence via SQLAlchemy.
Requires: docker compose up -d postgres && alembic upgrade head
"""
import os
from sqlalchemy import create_engine, text

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL", "")
        if not url:
            raise RuntimeError("DATABASE_URL not set")
        # asyncpg driver is for async use; use psycopg2 for sync persist
        sync_url = url.replace("postgresql+asyncpg://", "postgresql://")
        _engine = create_engine(sync_url, pool_pre_ping=True)
    return _engine


def save_run(run_result: dict) -> None:
    import json
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO agent_runs (trace_id, scenario, status, confidence,
                    confidence_rationale, artifacts, created_at)
                VALUES (:trace_id, :scenario, :status, :confidence,
                    :confidence_rationale, CAST(:artifacts AS jsonb), :created_at)
                ON CONFLICT (trace_id) DO NOTHING
                """
            ),
            {
                "trace_id": run_result["trace_id"],
                "scenario": run_result["scenario"],
                "status": run_result["status"],
                "confidence": run_result.get("confidence"),
                "confidence_rationale": run_result.get("confidence_rationale"),
                "artifacts": json.dumps(run_result.get("artifacts", {})),
                "created_at": run_result["created_at"],
            },
        )
