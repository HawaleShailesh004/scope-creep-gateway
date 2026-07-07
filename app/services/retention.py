from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

RESOLVED_STATUSES = ("paid", "dismissed")


def purge_expired_text() -> dict[str, int]:
    """Null raw message quotes on resolved or expired rows; keep structured fields."""
    supabase = get_supabase()
    counts = {"change_orders": 0, "absorbed_items": 0}

    projects = (
        supabase.table("projects")
        .select("id, retention_days")
        .execute()
        .data
        or []
    )
    default_retention = 30

    for project in projects:
        retention_days = project.get("retention_days") or default_retention
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=retention_days)
        ).isoformat()
        project_id = project["id"]

        resolved = (
            supabase.table("change_orders")
            .select("id")
            .eq("project_id", project_id)
            .in_("status", list(RESOLVED_STATUSES))
            .not_.is_("trigger_text", "null")
            .execute()
            .data
            or []
        )
        for row in resolved:
            supabase.table("change_orders").update({"trigger_text": None}).eq(
                "id", row["id"]
            ).execute()
            counts["change_orders"] += 1

        expired = (
            supabase.table("change_orders")
            .select("id")
            .eq("project_id", project_id)
            .lt("created_at", cutoff)
            .not_.is_("trigger_text", "null")
            .execute()
            .data
            or []
        )
        for row in expired:
            supabase.table("change_orders").update({"trigger_text": None}).eq(
                "id", row["id"]
            ).execute()
            counts["change_orders"] += 1

        absorbed = (
            supabase.table("absorbed_items")
            .select("id")
            .eq("project_id", project_id)
            .lt("created_at", cutoff)
            .not_.is_("trigger_text", "null")
            .execute()
            .data
            or []
        )
        for row in absorbed:
            supabase.table("absorbed_items").update({"trigger_text": None}).eq(
                "id", row["id"]
            ).execute()
            counts["absorbed_items"] += 1

    if counts["change_orders"] or counts["absorbed_items"]:
        logger.info("retention_purge %s", counts)
    return counts
