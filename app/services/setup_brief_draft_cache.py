from __future__ import annotations

import time
from typing import Any

_DRAFT_TTL_SECONDS = 600
_drafts: dict[str, tuple[float, dict[str, Any]]] = {}


def _key(user_id: str, channel_id: str) -> str:
    return f"{user_id}:{channel_id}"


def store_draft(*, user_id: str, channel_id: str, extracted: dict[str, Any]) -> None:
    _drafts[_key(user_id, channel_id)] = (time.monotonic(), extracted)


def pop_draft(*, user_id: str, channel_id: str) -> dict[str, Any] | None:
    entry = _drafts.pop(_key(user_id, channel_id), None)
    if not entry:
        return None
    stored_at, payload = entry
    if time.monotonic() - stored_at > _DRAFT_TTL_SECONDS:
        return None
    return payload


def prefill_from_extracted(data: dict[str, Any]) -> dict[str, Any]:
    deliverables = [
        str(item).strip()
        for item in (data.get("deliverables") or [])
        if str(item).strip()
    ]
    exclusions = [
        str(item).strip()
        for item in (data.get("exclusions") or [])
        if str(item).strip()
    ]
    revision = data.get("revision_limit")
    budget = data.get("budget")
    budget_str = None
    if budget is not None:
        try:
            number = float(budget)
            budget_str = str(int(number)) if number == int(number) else str(number)
        except (TypeError, ValueError):
            budget_str = None
    return {
        "project_name": (data.get("project_name") or "").strip() or None,
        "deliverables": deliverables or None,
        "exclusions": exclusions or None,
        "budget": budget_str,
        "deadline": data.get("deadline") or None,
        "client_label": (data.get("client_label") or "").strip() or None,
        "revision_limit": str(revision) if revision is not None else None,
        "client_slack_id": (data.get("suggested_client_user_id") or "").strip() or None,
    }


def assess_extracted_brief(extracted: dict[str, Any]) -> dict[str, Any]:
    """Score how much required brief data the extractor recovered."""
    project_name = (extracted.get("project_name") or "").strip()
    deliverables = [
        str(item).strip()
        for item in (extracted.get("deliverables") or [])
        if str(item).strip()
    ]
    has_name = bool(project_name)
    has_deliverables = bool(deliverables)

    missing: list[str] = []
    if not has_name:
        missing.append("project name")
    if not has_deliverables:
        missing.append("deliverables")
    missing.append("client")

    if not has_name and not has_deliverables:
        tier = "insufficient"
    elif has_name and has_deliverables:
        tier = "good"
    else:
        tier = "partial"

    return {
        "tier": tier,
        "missing": missing,
        "has_name": has_name,
        "has_deliverables": has_deliverables,
    }
