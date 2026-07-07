from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from db.supabase_client import get_supabase

CAPACITY_HOURS_THRESHOLD = 8.0


def _weekly_capacity_hours() -> float:
    raw = os.environ.get("WEEKLY_CAPACITY_HOURS", "40").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 40.0


def _period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # week: Monday 00:00 UTC
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start - timedelta(days=start.weekday())


def _freelancer_project_ids(freelancer_slack_id: str) -> list[str]:
    supabase = get_supabase()
    rows = (
        supabase.table("projects")
        .select("id")
        .eq("freelancer_slack_id", freelancer_slack_id)
        .execute()
        .data
        or []
    )
    return [row["id"] for row in rows]


def absorbed_hours(
    freelancer_slack_id: str,
    *,
    period: str = "week",
) -> dict[str, Any]:
    """Sum absorbed hours across all projects for a freelancer in the period."""
    project_ids = _freelancer_project_ids(freelancer_slack_id)
    if not project_ids:
        return {"hours": 0.0, "value": 0.0, "count": 0, "client_count": 0}

    since = _period_start(period).isoformat()
    supabase = get_supabase()
    rows = (
        supabase.table("absorbed_items")
        .select("estimated_hours, estimated_value, client_id, created_at")
        .in_("project_id", project_ids)
        .gte("created_at", since)
        .execute()
        .data
        or []
    )
    hours = sum(float(r.get("estimated_hours") or 0) for r in rows)
    value = sum(float(r.get("estimated_value") or 0) for r in rows)
    clients = {r.get("client_id") for r in rows if r.get("client_id")}
    return {
        "hours": round(hours, 1),
        "value": value,
        "count": len(rows),
        "client_count": len(clients),
    }


def absorbed_hours_by_client(
    freelancer_slack_id: str,
    *,
    period: str = "week",
) -> list[dict[str, Any]]:
    project_ids = _freelancer_project_ids(freelancer_slack_id)
    if not project_ids:
        return []

    since = _period_start(period).isoformat()
    supabase = get_supabase()
    rows = (
        supabase.table("absorbed_items")
        .select("estimated_hours, estimated_value, client_id, created_at")
        .in_("project_id", project_ids)
        .gte("created_at", since)
        .execute()
        .data
        or []
    )

    by_client: dict[str, dict[str, Any]] = {}
    for row in rows:
        cid = row.get("client_id") or "unknown"
        bucket = by_client.setdefault(
            cid, {"client_id": cid, "hours": 0.0, "value": 0.0, "count": 0}
        )
        bucket["hours"] += float(row.get("estimated_hours") or 0)
        bucket["value"] += float(row.get("estimated_value") or 0)
        bucket["count"] += 1

    result = sorted(by_client.values(), key=lambda x: x["hours"], reverse=True)
    for item in result:
        item["hours"] = round(item["hours"], 1)
    return result


def top_absorbed_client_label(
    freelancer_slack_id: str,
    *,
    period: str = "week",
) -> str | None:
    breakdown = absorbed_hours_by_client(freelancer_slack_id, period=period)
    if not breakdown:
        return None
    top = breakdown[0]
    client_id = top.get("client_id")
    if not client_id or client_id == "unknown":
        return None
    from services.clients import get_client

    client = get_client(client_id)
    if client:
        return client.get("client_label") or f"<@{client.get('client_slack_id')}>"
    return None


def capacity_nudge(
    freelancer_slack_id: str,
    *,
    additional_hours: float = 0.0,
    period: str = "week",
) -> str | None:
    totals = absorbed_hours(freelancer_slack_id, period=period)
    projected = totals["hours"] + additional_hours
    if projected < CAPACITY_HOURS_THRESHOLD:
        return None
    return str(round(projected, 1))


def capacity_pct_of_week(hours: float) -> int:
    cap = _weekly_capacity_hours()
    return min(100, round((hours / cap) * 100))
