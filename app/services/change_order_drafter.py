from __future__ import annotations

import json
import os

from groq import Groq

from services.brief_template import format_budget
from services.drafter_prompts import CHANGE_ORDER_PROMPT_VERSIONS

_client: Groq | None = None

DRAFTER_MODEL = "llama-3.3-70b-versatile"
SYSTEM = CHANGE_ORDER_PROMPT_VERSIONS["v3"]


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY must be set in .env")
        _client = Groq(api_key=api_key)
    return _client


def draft_change_order(
    *,
    brief_markdown: str,
    deliverables: list[str],
    trigger_text: str,
    task_summary: str | None,
    budget_total: float | int | None,
    currency: str = "INR",
    proposed_cost_so_far: float = 0,
) -> dict:
    remaining = None
    if budget_total is not None:
        remaining = max(float(budget_total) - proposed_cost_so_far, 0)

    user = f"""PROJECT BRIEF:
{brief_markdown}

DELIVERABLES (in scope):
{chr(10).join("- " + d for d in deliverables)}

CLIENT REQUEST (out of scope):
"{trigger_text}"

TASK SUMMARY: {task_summary or "Additional scope"}

ORIGINAL BUDGET: {format_budget(budget_total, currency)}
ALREADY PROPOSED ADD-ONS: {format_budget(proposed_cost_so_far, currency)}
REMAINING BUDGET HEADROOM: {format_budget(remaining, currency) if remaining is not None else "unknown"}

Draft the change order."""

    resp = _get_client().chat.completions.create(
        model=DRAFTER_MODEL,
        max_tokens=400,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)
