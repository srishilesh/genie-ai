"""
Persists the AgentRunResult to PostgreSQL.
DB models and Alembic migrations must be set up before this is active.
Falls back to a local JSON log if DB is unavailable.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)
_LOG_DIR = Path("working")


def persist(run_result: dict) -> None:
    try:
        from src.db.session import save_run
        save_run(run_result)
    except Exception as exc:
        log.warning("DB persist failed (%s) — writing to working/runs.jsonl instead", exc)
        _LOG_DIR.mkdir(exist_ok=True)
        with (_LOG_DIR / "runs.jsonl").open("a") as f:
            f.write(json.dumps({**run_result, "_logged_at": datetime.now(timezone.utc).isoformat()}) + "\n")
