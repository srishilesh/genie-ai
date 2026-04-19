"""
Pydantic schemas for every LLM request and response in the pipeline.
"""
from pydantic import BaseModel, Field

from src.schemas.report import Comparison, ResearchReport, Citation


# ── Shared ────────────────────────────────────────────────────────────────────

class LLMMessage(BaseModel):
    role: str
    content: str


class ChunkContext(BaseModel):
    source_id: str
    source_type: str
    collection: str = ""
    text: str
    title: str = ""
    url: str = ""


# ── Planner ───────────────────────────────────────────────────────────────────

class PlannerRequest(BaseModel):
    query: str
    messages: list[LLMMessage]


class PlannerResponse(BaseModel):
    sub_questions: list[str] = Field(min_length=1)


# ── Comparator ────────────────────────────────────────────────────────────────

class ComparatorRequest(BaseModel):
    query: str
    chunks: list[ChunkContext]
    messages: list[LLMMessage]


class ComparatorResponse(BaseModel):
    comparisons: list[Comparison]


# ── Writer ────────────────────────────────────────────────────────────────────

class WriterRequest(BaseModel):
    query: str
    chunks: list[ChunkContext]
    comparisons: list[Comparison]
    sources_used: list[str]
    messages: list[LLMMessage]


class WriterResponse(BaseModel):
    report: ResearchReport


# ── HackerNews relevance filter ───────────────────────────────────────────────

class HNFilterRequest(BaseModel):
    query: str
    summaries: list[str]
    messages: list[LLMMessage]


class HNFilterResponse(BaseModel):
    indices: list[int]


# ── HackerNews query variation ────────────────────────────────────────────────

class HNVariationRequest(BaseModel):
    query: str
    messages: list[LLMMessage]


class HNVariationResponse(BaseModel):
    variations: list[str] = Field(min_length=1)


# ── Re-planner ────────────────────────────────────────────────────────────────

class RePlannerRequest(BaseModel):
    query: str
    prev_sub_questions: list[str]
    confidence: float
    rationale: str
    messages: list[LLMMessage]


class RePlannerResponse(BaseModel):
    sub_questions: list[str] = Field(min_length=1)


# ── LLM Judge ─────────────────────────────────────────────────────────────────

class LLMJudgeRequest(BaseModel):
    query: str
    messages: list[LLMMessage]


class LLMJudgeResponse(BaseModel):
    query_relevance: float = Field(ge=0.0, le=1.0)
    factual_grounding: float = Field(ge=0.0, le=1.0)
    coverage: float = Field(ge=0.0, le=1.0)
    reasoning: str

    @property
    def composite(self) -> float:
        return round((self.query_relevance + self.factual_grounding + self.coverage) / 3, 3)
