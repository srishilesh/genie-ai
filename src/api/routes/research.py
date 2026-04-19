from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.graph import research_graph
from src.schemas.report import ResearchReport

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    trace_id: str | None = None
    status: str
    confidence: float | None = None
    report: ResearchReport | None = None


@router.post("", response_model=ResearchResponse)
def run_research(body: ResearchRequest) -> ResearchResponse:
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")

    result = research_graph.invoke(body.query)
    return ResearchResponse(**result)
