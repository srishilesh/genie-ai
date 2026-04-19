from fastapi import APIRouter
from pydantic import BaseModel

from src.api.utils import validate_query
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
    pipeline: list[dict] | None = None


@router.post("", response_model=ResearchResponse)
def run_research(body: ResearchRequest) -> ResearchResponse:
    query = validate_query(body.query)
    result = research_graph.invoke(query)
    return ResearchResponse(**result)
