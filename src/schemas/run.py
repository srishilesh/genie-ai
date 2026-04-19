from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class RunStatus(str, Enum):
    completed = "completed"
    needs_review = "needs_review"
    failed = "failed"


class StageStatus(str, Enum):
    success = "success"
    skipped = "skipped"
    retrying = "retrying"
    failed = "failed"


class Stage(BaseModel):
    name: str
    status: StageStatus
    started_at: datetime
    ended_at: datetime | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    tool_calls: list[dict] = []
    errors: list[dict] = []


class AgentRunResult(BaseModel):
    trace_id: str
    scenario: str = "scenario_3_research"
    status: RunStatus
    created_at: datetime
    updated_at: datetime | None = None
    confidence: float | None = None
    confidence_rationale: str | None = None
    decision: dict | None = None
    artifacts: dict | None = None
    stages: list[Stage] = []
