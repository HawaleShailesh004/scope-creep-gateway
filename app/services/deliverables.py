from __future__ import annotations

import re

from db.supabase_client import get_supabase, run_query

_GENERIC_TOKENS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "can",
        "you",
        "also",
        "please",
        "pls",
        "section",
        "page",
        "redesign",
        "design",
        "update",
        "align",
        "new",
        "add",
        "work",
        "project",
        "original",
        "brief",
        "additional",
    }
)


def _content_tokens(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if len(word) >= 3 and word not in _GENERIC_TOKENS
    }


def _normalize_description(text: str) -> str:
    return text.split(".")[0][:200].strip()


def load_effective_deliverables(project_id: str) -> list[dict]:
    """All deliverable rows including exclusions (stored with origin=exclusion)."""
    result = run_query(
        lambda sb: sb.table("deliverables").select("*").eq("project_id", project_id)
    )
    return result.data or []


def load_in_scope_deliverables(project_id: str) -> list[dict]:
    return [
        row
        for row in load_effective_deliverables(project_id)
        if row.get("origin") != "exclusion"
    ]


def load_exclusions(project_id: str) -> list[str]:
    return [
        row["description"]
        for row in load_effective_deliverables(project_id)
        if row.get("origin") == "exclusion" and row.get("description")
    ]


def deliverable_descriptions(project_id: str) -> list[str]:
    return [row["description"] for row in load_in_scope_deliverables(project_id)]


def save_exclusions(project_id: str, exclusions: list[str]) -> None:
    supabase = get_supabase()
    supabase.table("deliverables").delete().eq("project_id", project_id).eq(
        "origin", "exclusion"
    ).execute()
    rows = [
        {
            "project_id": project_id,
            "description": item.strip(),
            "origin": "exclusion",
        }
        for item in exclusions
        if item.strip()
    ]
    if rows:
        supabase.table("deliverables").insert(rows).execute()


def add_change_order_deliverable(
    *,
    project_id: str,
    description: str,
    revision_limit: int | None = None,
) -> str:
    supabase = get_supabase()
    row = {
        "project_id": project_id,
        "description": _normalize_description(description),
        "origin": "change_order",
        "revision_limit": revision_limit,
    }
    result = supabase.table("deliverables").insert(row).execute()
    return result.data[0]["id"]


def find_deliverable_by_description(
    project_id: str, description: str
) -> dict | None:
    rows = load_effective_deliverables(project_id)
    needle = description.strip().lower()
    for row in rows:
        if row.get("description", "").strip().lower() == needle:
            return row
    return None


def message_covered_by_deliverables(message: str, deliverables: list[str]) -> bool:
    """Dedup helper only — not used to skip classification (classifier reads the brief)."""
    msg_tokens = _content_tokens(message)
    if not msg_tokens:
        return False

    for description in deliverables:
        desc_tokens = _content_tokens(description)
        if not desc_tokens:
            continue
        # Only treat as duplicate when the message mentions every distinctive token
        # in the deliverable (revision / follow-up on same item).
        if desc_tokens.issubset(msg_tokens):
            return True
    return False


def ensure_deliverable_for_paid_order(change_order: dict) -> bool:
    """Insert a deliverable for a paid CO if one is not already represented."""
    project_id = change_order.get("project_id")
    if not project_id:
        return False

    description = _normalize_description(
        change_order.get("task_description")
        or change_order.get("trigger_text")
        or ""
    )
    if not description:
        return False

    existing = deliverable_descriptions(project_id)
    if message_covered_by_deliverables(description, existing):
        return False

    add_change_order_deliverable(project_id=project_id, description=description)
    return True


def sync_paid_change_orders_to_deliverables(project_id: str) -> int:
    """Backfill deliverables from paid change orders (idempotent)."""
    paid_orders = (
        run_query(
            lambda sb: sb.table("change_orders")
            .select("*")
            .eq("project_id", project_id)
            .eq("status", "paid")
        ).data
        or []
    )

    added = 0
    for order in paid_orders:
        if ensure_deliverable_for_paid_order(order):
            added += 1
    return added
