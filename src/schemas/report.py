from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_id: str
    location: str
    used_for: str


class Comparison(BaseModel):
    claim: str
    agreement: list[str]
    conflicts: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class ResearchReport(BaseModel):
    topic: str
    executive_summary: str
    findings: list[str]
    comparisons: list[Comparison]
    recommendation: str | None = None
    open_questions: list[str]
    sources_used: list[str]
    citations: list[Citation] | None = None
