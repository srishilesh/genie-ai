import json
import os
from openai import OpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai

from src.prompts import PLANNER_SYSTEM, PLANNER_USER
from src.schemas.llm import LLMMessage, PlannerRequest, PlannerResponse

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
    parsed = raw if isinstance(raw, list) else next(iter(raw.values()))
    result = PlannerResponse(sub_questions=parsed)
    return result.sub_questions
