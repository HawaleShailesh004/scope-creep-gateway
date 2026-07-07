from __future__ import annotations

from db.supabase_client import get_supabase


def count_revisions(deliverable_id: str) -> int:
    supabase = get_supabase()
    result = (
        supabase.table("revisions")
        .select("id", count="exact")
        .eq("deliverable_id", deliverable_id)
        .execute()
    )
    return result.count or 0


def log_revision(*, deliverable_id: str, trigger_message_ts: str | None) -> str:
    supabase = get_supabase()
    row = {
        "deliverable_id": deliverable_id,
        "trigger_message_ts": trigger_message_ts,
    }
    result = supabase.table("revisions").insert(row).execute()
    return result.data[0]["id"]


def revision_limit_breached(deliverable: dict) -> bool:
    limit = deliverable.get("revision_limit")
    if limit is None:
        return False
    return count_revisions(deliverable["id"]) >= int(limit)


def find_target_deliverable(
    project_id: str, target_name: str | None
) -> dict | None:
    if not target_name:
        return None
    supabase = get_supabase()
    rows = (
        supabase.table("deliverables")
        .select("*")
        .eq("project_id", project_id)
        .execute()
        .data
        or []
    )
    needle = target_name.strip().lower()
    for row in rows:
        desc = row.get("description", "").lower()
        if needle in desc or desc in needle:
            return row
    return None
