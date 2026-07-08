from __future__ import annotations

from typing import Any

from db.supabase_client import get_supabase, run_query


def is_analysis_allowed(project: dict[str, Any]) -> bool:
    """Classification runs only after disclosure and when not disabled."""
    if not project.get("disclosure_ts"):
        return False
    if project.get("classification_enabled") is False:
        return False
    return True


def save_disclosure_ts(project_id: str, disclosure_ts: str) -> None:
    supabase = get_supabase()
    supabase.table("projects").update({"disclosure_ts": disclosure_ts}).eq(
        "id", project_id
    ).execute()


def set_classification_enabled(project_id: str, enabled: bool) -> None:
    supabase = get_supabase()
    supabase.table("projects").update({"classification_enabled": enabled}).eq(
        "id", project_id
    ).execute()


def load_project_by_channel(channel_id: str) -> dict | None:
    result = run_query(
        lambda sb: sb.table("projects")
        .select("*")
        .eq("slack_channel_id", channel_id)
        .limit(1)
    )
    return result.data[0] if result.data else None
