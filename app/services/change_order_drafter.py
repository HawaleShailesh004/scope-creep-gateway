from __future__ import annotations

import json
import os

import anthropic

from services.brief_template import format_budget

_client: anthropic.Anthropic | None = None

SYSTEM = """You draft change orders for freelance projects.
Given the project brief and an out-of-scope client request, propose:
- task_description: 1-2 sentences for the client-facing change order
- estimated_cost: numeric amount in the project's currency (reasonable vs budget)
- timeline_impact_days: integer days added to the timeline

Return ONLY strict JSON:
{"task_description": "...",
 "estimated_cost": 8000,
 "timeline_impact_days": 3}"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY must be set in .env")
        _client = anthropic.Anthropic(api_key=api_key)
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

    resp = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        temperature=0,
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    text = resp.content[0].text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)
