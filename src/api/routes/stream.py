import json
import logging
import traceback
import uuid
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from langsmith import trace as ls_trace
from pydantic import BaseModel

from src.api.utils import validate_query
from src.agents.planner import plan as _plan, replan as _replan
from src.agents.gatherer import gather as _gather
from src.agents.comparator import compare as _compare
from src.agents.writer import write as _write
from src.agents.scorer import score as _score
from src.agents.persist import persist as _persist

log = logging.getLogger(__name__)
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
    current_node = "pipeline"

    try:
        with ls_trace(
            name="research_pipeline",
            run_type="chain",
            metadata={"trace_id": trace_id, "query": query},
        ):
            current_node = "planner"
            yield _sse({"node": "planner", "state": "running"})
            sub_questions = await asyncio.to_thread(_plan, query)
            yield _sse({"node": "planner", "state": "done", "output": {"sub_questions": sub_questions}})

            current_node = "gatherer"
            yield _sse({"node": "gatherer", "state": "running"})
            gather_result = await asyncio.to_thread(_gather, query, sub_questions)
            chunks = gather_result["chunks"]
            selected = gather_result["selected_source"]
            local_chunks = [c for c in chunks if c.get("collection") != "marre_hn"]
            hn_chunks = [c for c in chunks if c.get("collection") == "marre_hn"]
            yield _sse({
                "node": "gatherer",
                "state": "done",
                "output": {
                    "selected_source": selected,
                    "hn_fetched": gather_result["hn_fetched"],
                    "hn_warning": gather_result.get("hn_warning"),
                    "local_avg_distance": gather_result["local_avg_distance"],
                    "hn_avg_distance": gather_result["hn_avg_distance"],
                    "chunk_count": len(chunks),
                    "local_count": len(local_chunks),
                    "hn_count": len(hn_chunks),
                    "chunks": [
                        {
                            "source_id": c["source_id"],
                            "source_type": c["source_type"],
                            "collection": c.get("collection", ""),
                            "title": c.get("title", ""),
                            "url": c.get("url", ""),
                            "preview": c["text"][:200],
                        }
                        for c in chunks
                    ],
                },
            })

            current_node = "comparator"
            yield _sse({"node": "comparator", "state": "running"})
            comparisons = await asyncio.to_thread(_compare, query, chunks)
            yield _sse({"node": "comparator", "state": "done", "output": {"comparisons": comparisons}})

            current_node = "writer"
            yield _sse({"node": "writer", "state": "running"})
            report = await asyncio.to_thread(_write, query, comparisons, chunks)
            yield _sse({"node": "writer", "state": "done"})

            current_node = "scorer"
            yield _sse({"node": "scorer", "state": "running"})
            report, confidence, rationale = await asyncio.to_thread(_score, report, query)
            yield _sse({"node": "scorer", "state": "done", "output": {"confidence": confidence, "rationale": rationale}})

            # ── Confidence retry (max 1) ──────────────────────────────────────
            if confidence < 0.7:
                yield _sse({"node": "replanner", "state": "running", "output": {"reason": f"confidence={confidence:.3f} < 0.7 — retrying with focused sub-questions"}})
                retry_sub_questions = await asyncio.to_thread(_replan, query, sub_questions, confidence, rationale)
                yield _sse({"node": "replanner", "state": "done", "output": {"sub_questions": retry_sub_questions}})

                yield _sse({"node": "gatherer", "state": "running"})
                retry_gather = await asyncio.to_thread(_gather, query, retry_sub_questions)
                retry_chunks = retry_gather["chunks"]
                yield _sse({"node": "gatherer", "state": "done", "output": {"chunk_count": len(retry_chunks), "selected_source": retry_gather["selected_source"], "retry": True}})

                yield _sse({"node": "comparator", "state": "running"})
                retry_comparisons = await asyncio.to_thread(_compare, query, retry_chunks)
                yield _sse({"node": "comparator", "state": "done", "output": {"comparisons": retry_comparisons, "retry": True}})

                yield _sse({"node": "writer", "state": "running"})
                retry_report = await asyncio.to_thread(_write, query, retry_comparisons, retry_chunks)
                yield _sse({"node": "writer", "state": "done", "output": {"retry": True}})

                yield _sse({"node": "scorer", "state": "running"})
                retry_report, retry_confidence, retry_rationale = await asyncio.to_thread(_score, retry_report, query)
                yield _sse({"node": "scorer", "state": "done", "output": {"confidence": retry_confidence, "rationale": retry_rationale, "retry": True}})

                # Use retry result if it improved, otherwise keep original
                if retry_confidence >= confidence:
                    report, confidence, rationale = retry_report, retry_confidence, retry_rationale
                    sub_questions = retry_sub_questions

            status = "needs_review" if confidence < 0.7 else "completed"

            current_node = "persist"
            yield _sse({"node": "persist", "state": "running"})
            run_result = {
                "trace_id": trace_id,
                "scenario": "scenario_3_research",
                "status": status,
                "created_at": created_at,
                "confidence": confidence,
                "confidence_rationale": rationale,
                "artifacts": {"report": report.model_dump()},
                "stages": ["planner", "gatherer", "comparator", "writer", "scorer"],
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

    except Exception as exc:
        log.error("Pipeline failed at node=%s: %s", current_node, exc, exc_info=True)
        yield _sse({
            "node": current_node,
            "state": "error",
            "error": str(exc),
            "trace": traceback.format_exc().splitlines()[-3:],
            "trace_id": trace_id,
        })


@router.post("/stream")
async def stream_research(
    body: StreamRequest,
    x_api_key: str | None = Header(default=None),
):
    query = validate_query(body.query)
    return StreamingResponse(
        _pipeline(query, x_api_key),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
