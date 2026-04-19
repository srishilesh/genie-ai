import json
import logging
import os

from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import OpenAI

from src.prompts import LLM_JUDGE_SYSTEM, LLM_JUDGE_USER
from src.schemas.llm import LLMJudgeRequest, LLMJudgeResponse, LLMMessage
from src.schemas.report import ResearchReport

log = logging.getLogger(__name__)
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = wrap_openai(OpenAI(api_key=os.environ["OPENAI_API_KEY"]))
    return _client


@traceable(name="structural_scorer")
def _structural_score(report: ResearchReport) -> tuple[float, list[str]]:
    points = 0.0
    reasons = []

    if len(report.sources_used) >= 3:
        points += 0.3
        reasons.append(f"{len(report.sources_used)} sources cited")
    elif report.sources_used:
        points += 0.15
        reasons.append(f"only {len(report.sources_used)} source(s) cited")

    comparisons_with_data = [c for c in report.comparisons if c.agreement or c.conflicts]
    if comparisons_with_data:
        ratio = len(comparisons_with_data) / max(len(report.comparisons), 1)
        points += 0.3 * ratio
        reasons.append(f"{len(comparisons_with_data)}/{len(report.comparisons)} comparisons supported")

    if report.findings:
        points += min(0.2, 0.05 * len(report.findings))
        reasons.append(f"{len(report.findings)} findings")

    if report.open_questions:
        penalty = min(0.1, 0.02 * len(report.open_questions))
        points -= penalty
        reasons.append(f"-{penalty:.2f} for {len(report.open_questions)} open questions")

    if report.recommendation:
        points += 0.1
        reasons.append("recommendation present")

    if report.citations:
        points += 0.1
        reasons.append("citations present")

    return round(max(0.0, min(1.0, points)), 3), reasons


@traceable(name="llm_judge", run_type="llm")
def _llm_judge(query: str, report: ResearchReport) -> LLMJudgeResponse:
    findings_preview = "; ".join(report.findings[:3]) if report.findings else "none"
    comparisons_preview = (
        "; ".join(c.claim for c in report.comparisons[:3]) if report.comparisons else "none"
    )
    messages = [
        LLMMessage(role="system", content=LLM_JUDGE_SYSTEM),
        LLMMessage(
            role="user",
            content=LLM_JUDGE_USER.format(
                query=query,
                executive_summary=report.executive_summary[:400],
                n_findings=len(report.findings),
                findings_preview=findings_preview,
                n_comparisons=len(report.comparisons),
                comparisons_preview=comparisons_preview,
                sources_used=", ".join(report.sources_used),
                n_open_questions=len(report.open_questions),
            ),
        ),
    ]
    request = LLMJudgeRequest(query=query, messages=messages)

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[m.model_dump() for m in request.messages],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = json.loads(response.choices[0].message.content)
    return LLMJudgeResponse(**raw)


@traceable(name="scorer")
def score(report: ResearchReport, query: str) -> tuple[ResearchReport, float, str]:
    structural, struct_reasons = _structural_score(report)

    try:
        judge = _llm_judge(query, report)
        llm_score = judge.composite
        llm_reasoning = judge.reasoning
    except Exception as exc:
        log.warning("LLM judge failed, using structural score only: %s", exc)
        llm_score = structural
        llm_reasoning = "LLM judge unavailable"

    # Composite: 40% structural + 60% LLM judge
    composite = round(0.4 * structural + 0.6 * llm_score, 3)

    rationale = (
        f"[structural={structural:.3f}] {'; '.join(struct_reasons)} | "
        f"[llm_judge={llm_score:.3f}] relevance={judge.query_relevance:.2f}, "
        f"grounding={judge.factual_grounding:.2f}, coverage={judge.coverage:.2f} — {llm_reasoning}"
        if llm_score != structural
        else "; ".join(struct_reasons)
    )

    return report, composite, rationale
