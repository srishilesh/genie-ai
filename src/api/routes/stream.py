import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents.classifier import classify as _classify
from src.agents.planner import plan as _plan
from src.agents.gatherer import gather as _gather
from src.agents.comparator import compare as _compare
from src.agents.writer import write as _write
from src.agents.scorer import score as _score
from src.agents.persist import persist as _persist

router = APIRouter(prefix="/research", tags=["research-stream"])


class StreamRequest(BaseModel):
    query: str


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _pipeline(query: str, api_key: str | None) -> AsyncGenerator[str, None]:
    import os
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    trace_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    yield _sse({"node": "classifier", "state": "running"})
    classification = await asyncio.to_thread(_classify, query)
    yield _sse({"node": "classifier", "state": "done", "output": {"classification": classification}})

    if classification != "research":
        yield _sse({"node": "done", "state": "casual", "trace_id": trace_id})
        return

    yield _sse({"node": "planner", "state": "running"})
    sub_questions = await asyncio.to_thread(_plan, query)
    yield _sse({"node": "planner", "state": "done", "output": {"sub_questions": sub_questions}})

    yield _sse({"node": "gatherer", "state": "running"})
    chunks = await asyncio.to_thread(_gather, query, sub_questions)
    rag_chunks = [c for c in chunks if c["source_id"] != "hackernews"]
    hn_chunks  = [c for c in chunks if c["source_id"] == "hackernews"]
    yield _sse({
        "node": "gatherer",
        "state": "done",
        "output": {
            "chunk_count": len(chunks),
            "rag_count": len(rag_chunks),
            "hn_count": len(hn_chunks),
            "chunks": [
                {
                    "source_id": c["source_id"],
                    "source_type": c["source_type"],
                    "preview": c["text"][:200],
                    **({"url": c["url"], "title": c["title"]} if c["source_id"] == "hackernews" else {}),
                }
                for c in chunks
            ],
        },
    })

    yield _sse({"node": "comparator", "state": "running"})
    comparisons = await asyncio.to_thread(_compare, query, chunks)
    yield _sse({"node": "comparator", "state": "done", "output": {"comparisons": comparisons}})

    yield _sse({"node": "writer", "state": "running"})
    report = await asyncio.to_thread(_write, query, comparisons, chunks)
    yield _sse({"node": "writer", "state": "done"})

    yield _sse({"node": "scorer", "state": "running"})
    report, confidence, rationale = await asyncio.to_thread(_score, report)
    yield _sse({"node": "scorer", "state": "done", "output": {"confidence": confidence, "rationale": rationale}})

    status = "needs_review" if confidence < 0.7 else "completed"

    yield _sse({"node": "persist", "state": "running"})
    run_result = {
        "trace_id": trace_id,
        "scenario": "scenario_3_research",
        "status": status,
        "created_at": created_at,
        "confidence": confidence,
        "confidence_rationale": rationale,
        "artifacts": {"report": report.model_dump()},
        "stages": ["classifier", "planner", "gatherer", "comparator", "writer", "scorer"],
        "query": query,
    }
    await asyncio.to_thread(_persist, run_result)
    yield _sse({"node": "persist", "state": "done"})

    yield _sse({
        "node": "done",
        "state": "completed",
        "trace_id": trace_id,
        "status": status,
        "confidence": confidence,
        "report": report.model_dump(),
    })


@router.post("/stream")
async def stream_research(
    body: StreamRequest,
    x_api_key: str | None = Header(default=None),
):
    return StreamingResponse(
        _pipeline(body.query, x_api_key),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
