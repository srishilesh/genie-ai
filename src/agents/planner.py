import json
import os
from openai import OpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai

from src.prompts import PLANNER_SYSTEM, PLANNER_USER, REPLANNER_SYSTEM, REPLANNER_USER
from src.schemas.llm import LLMMessage, PlannerRequest, PlannerResponse, RePlannerRequest, RePlannerResponse

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = wrap_openai(OpenAI(api_key=os.environ["OPENAI_API_KEY"]))
    return _client


@traceable(name="planner", run_type="llm")
def plan(query: str) -> list[str]:
    messages = [
        LLMMessage(role="system", content=PLANNER_SYSTEM),
        LLMMessage(role="user", content=PLANNER_USER.format(query=query)),
    ]
    request = PlannerRequest(query=query, messages=messages)

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[m.model_dump() for m in request.messages],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = json.loads(response.choices[0].message.content)
    parsed = raw if isinstance(raw, list) else raw.get("sub_questions", next(iter(raw.values())))

    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, ValueError):
            parsed = [q.strip() for q in parsed.splitlines() if q.strip()]

    try:
        result = PlannerResponse(sub_questions=parsed)
    except Exception:
        fallback = [str(parsed)] if parsed else [query]
        result = PlannerResponse(sub_questions=fallback)

    return result.sub_questions


@traceable(name="replanner", run_type="llm")
def replan(query: str, prev_sub_questions: list[str], confidence: float, rationale: str) -> list[str]:
    messages = [
        LLMMessage(role="system", content=REPLANNER_SYSTEM),
        LLMMessage(
            role="user",
            content=REPLANNER_USER.format(
                query=query,
                prev_sub_questions=json.dumps(prev_sub_questions),
                confidence=confidence,
                rationale=rationale,
            ),
        ),
    ]
    request = RePlannerRequest(
        query=query,
        prev_sub_questions=prev_sub_questions,
        confidence=confidence,
        rationale=rationale,
        messages=messages,
    )

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[m.model_dump() for m in request.messages],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = json.loads(response.choices[0].message.content)
    parsed = raw if isinstance(raw, list) else raw.get("sub_questions", next(iter(raw.values())))

    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, ValueError):
            parsed = [q.strip() for q in parsed.splitlines() if q.strip()]

    try:
        result = RePlannerResponse(sub_questions=parsed)
    except Exception:
        result = RePlannerResponse(sub_questions=[str(parsed)] if parsed else [query])

    return result.sub_questions
