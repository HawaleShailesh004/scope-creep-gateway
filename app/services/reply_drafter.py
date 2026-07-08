from __future__ import annotations

import os

from groq import Groq

from services.brief_template import format_budget
from services.drafter_prompts import REPLY_PROMPT_VERSIONS

_client: Groq | None = None

DRAFTER_MODEL = "llama-3.3-70b-versatile"
REPLY_SYSTEM = REPLY_PROMPT_VERSIONS["v3"]

TONE_GUIDANCE = {
    "warm": (
        "Warm and collaborative — acknowledge the client's idea, explain scope gently, "
        "and invite a conversation about a change order."
    ),
    "neutral": (
        "Professional and clear — state what's in scope, what isn't, and the path to add "
        "the work without sounding harsh."
    ),
    "firm": (
        "Direct but respectful — name that this is outside the agreed brief and that "
        "additional work requires a change order before starting."
    ),
}


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY must be set in .env")
        _client = Groq(api_key=api_key)
    return _client


def draft_client_reply(
    *,
    brief_markdown: str,
    deliverables: list[str],
    client_message: str,
    task_summary: str | None,
    estimated_cost: float | None,
    timeline_impact_days: int | None,
    currency: str,
    tone: str = "neutral",
) -> str:
    """Generate a freelancer-private client-facing message. Never auto-sent."""
    tone = tone if tone in TONE_GUIDANCE else "neutral"
    cost_line = (
        format_budget(estimated_cost, currency)
        if estimated_cost is not None
        else "to be confirmed"
    )
    days_line = (
        f"+{timeline_impact_days} days"
        if timeline_impact_days is not None
        else "to be confirmed"
    )

    user = f"""PROJECT BRIEF:
{brief_markdown}

IN-SCOPE DELIVERABLES:
{chr(10).join("- " + d for d in deliverables)}

CLIENT'S REQUEST (out of scope):
"{client_message}"

TASK SUMMARY: {task_summary or "Additional scope"}

INDICATIVE CHANGE ORDER (if billing):
- Cost: {cost_line}
- Timeline: {days_line}

TONE: {tone} — {TONE_GUIDANCE[tone]}

Write a short message the freelancer can copy-paste to the client (2-4 sentences).
Do not mention AI, bots, or Scope Creep Gateway.
Use {currency} when citing money.
Return only the message text, no quotes or labels."""

    resp = _get_client().chat.completions.create(
        model=DRAFTER_MODEL,
        max_tokens=350,
        temperature=0.4,
        messages=[
            {"role": "system", "content": REPLY_SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    return (resp.choices[0].message.content or "").strip()
