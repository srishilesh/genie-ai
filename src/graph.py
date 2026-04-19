import uuid
from datetime import datetime, timezone

from langgraph.func import entrypoint, task

from src.agents.classifier import classify as _classify
from src.agents.planner import plan as _plan
from src.agents.gatherer import gather as _gather
from src.agents.comparator import compare as _compare
from src.agents.writer import write as _write
from src.agents.scorer import score as _score
from src.agents.persist import persist as _persist


@task
def classify(query: str) -> str:
    return _classify(query)


@task
def plan(query: str) -> list[str]:
    return _plan(query)


@task
def gather(query: str, sub_questions: list[str], research_type: str) -> list[dict]:
    return _gather(query, sub_questions, research_type=research_type)


@task
def compare(query: str, chunks: list[dict]) -> list[dict]:
    return _compare(query, chunks)


@task
def write(query: str, comparisons: list[dict], chunks: list[dict]):
    return _write(query, comparisons, chunks)


@task
def score(report):
    return _score(report)


@task
def persist(run_result: dict) -> None:
    _persist(run_result)


@entrypoint()
def research_graph(query: str) -> dict:
    trace_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    classification = classify(query).result()
    if classification == "casual":
        return {
            "status": "casual",
            "confidence": None,
            "report": None,
            "trace_id": trace_id,
            "pipeline": [
                {"node": "classifier", "output": {"classification": classification}},
            ],
        }

    research_type = classification  # local_research | hn_research

    sub_questions = plan(query).result()
    chunks = gather(query, sub_questions, research_type).result()
    comparisons = compare(query, chunks).result()
    report = write(query, comparisons, chunks).result()
    report, confidence, rationale = score(report).result()

    status = "needs_review" if confidence < 0.7 else "completed"

    pipeline = [
        {"node": "classifier", "output": {"classification": classification, "research_type": research_type}},
        {"node": "planner", "output": {"sub_questions": sub_questions}},
        {
            "node": "gatherer",
            "output": {
                "research_type": research_type,
                "chunk_count": len(chunks),
                "chunks": [
                    {
                        "source_id": c["source_id"],
                        "source_type": c["source_type"],
                        "collection": c.get("collection", ""),
                        "title": c.get("title", ""),
                        "preview": c["text"][:200],
                    }
                    for c in chunks
                ],
            },
        },
        {"node": "comparator", "output": {"comparisons": comparisons}},
        {"node": "scorer", "output": {"confidence": confidence, "rationale": rationale}},
    ]

    run_result = {
        "trace_id": trace_id,
        "scenario": "scenario_3_research",
        "status": status,
        "created_at": created_at,
        "confidence": confidence,
        "confidence_rationale": rationale,
        "artifacts": {"report": report.model_dump()},
        "stages": [p["node"] for p in pipeline],
    }

    persist(run_result).result()

    return {
        "status": status,
        "confidence": confidence,
        "report": report.model_dump(),
        "trace_id": trace_id,
        "pipeline": pipeline,
    }
