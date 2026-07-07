from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import anthropic
from slack_sdk.web.async_client import AsyncWebClient

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY must be set in .env")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


async def fetch_channel_conversation(
    bot_token: str,
    channel_id: str,
    *,
    limit: int = 50,
) -> list[dict[str, str]]:
    client = AsyncWebClient(token=bot_token)
    resp = await client.conversations_history(channel=channel_id, limit=limit)
    messages = resp.get("messages") or []
    lines: list[dict[str, str]] = []
    for msg in reversed(messages):
        if msg.get("subtype") in ("channel_join", "bot_message"):
            continue
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        user = msg.get("user") or msg.get("bot_id") or "unknown"
        lines.append({"user_id": user, "text": text})
    return lines


def _format_conversation(
    messages: list[dict[str, str]],
    *,
    user_labels: dict[str, str] | None = None,
) -> str:
    labels = user_labels or {}
    parts = []
    for msg in messages:
        who = labels.get(msg["user_id"], msg["user_id"])
        parts.append(f"[{who}] {msg['text']}")
    return "\n".join(parts)


def extract_brief_from_conversation(
    conversation: str,
    *,
    freelancer_hint: str = "",
) -> dict[str, Any]:
    """Propose structured brief fields from channel kickoff chat."""
    user = f"""You are helping a freelancer set up a project brief from Slack channel history.

Freelancer hint: {freelancer_hint or "none"}

CHANNEL CONVERSATION:
{conversation}

Return ONLY strict JSON:
{{
  "project_name": "string",
  "deliverables": ["in-scope deliverable labels, one concept each"],
  "exclusions": ["things discussed but explicitly NOT included unless agreed later"],
  "budget": number or null,
  "currency": "INR or other ISO code",
  "deadline": "YYYY-MM-DD or null",
  "revision_limit": integer or null,
  "client_label": "company or client name or null",
  "suggested_client_user_id": "Slack user id of the client if obvious from [U...] labels, else null"
}}

Rules:
- Deliverables = work the freelancer agreed to do.
- Exclusions = items the client mentioned but were deferred, out of budget, or explicitly "later" / "phase 2".
- Use null for fields you cannot infer. Be conservative on deliverables."""

    resp = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=900,
        temperature=0,
        messages=[{"role": "user", "content": user}],
    )
    text = resp.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    data = json.loads(text)
    for key in ("deliverables", "exclusions"):
        if not isinstance(data.get(key), list):
            data[key] = []
    return data


async def extract_brief_from_channel(
    bot_token: str,
    channel_id: str,
    *,
    user_labels: dict[str, str] | None = None,
    freelancer_hint: str = "",
) -> dict[str, Any]:
    messages = await fetch_channel_conversation(bot_token, channel_id)
    if not messages:
        raise ValueError("No conversation found in this channel yet.")
    conversation = _format_conversation(messages, user_labels=user_labels)
    return extract_brief_from_conversation(conversation, freelancer_hint=freelancer_hint)
