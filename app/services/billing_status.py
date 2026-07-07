from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from db.supabase_client import get_supabase

# flagged = internal only; proposed = billed awaiting approval; paid = approved; dismissed = withdrawn


def _period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta

    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start - timedelta(days=start.weekday())


def _summarize_orders(orders: list[dict[str, Any]]) -> dict[str, Any]:
    billed = approved = pending = withdrawn = 0.0
    billed_count = approved_count = pending_count = withdrawn_count = 0

    for order in orders:
        status = order.get("status") or "flagged"
        cost = float(order.get("estimated_cost") or order.get("estimated_value") or 0)
        if status == "proposed":
            billed += cost
            pending += cost
            billed_count += 1
            pending_count += 1
        elif status == "paid":
            billed += cost
            approved += cost
            billed_count += 1
            approved_count += 1
        elif status == "dismissed":
            withdrawn += cost
            withdrawn_count += 1

    return {
        "billed": billed,
        "approved": approved,
        "pending": pending,
        "withdrawn": withdrawn,
        "billed_count": billed_count,
        "approved_count": approved_count,
        "pending_count": pending_count,
        "withdrawn_count": withdrawn_count,
    }


def billing_summary_for_projects(
    project_ids: list[str],
    *,
    period: str = "week",
) -> dict[str, Any]:
    if not project_ids:
        return _summarize_orders([])

    since = _period_start(period).isoformat()
    supabase = get_supabase()
    rows = (
        supabase.table("change_orders")
        .select("status, estimated_cost, estimated_value, created_at")
        .in_("project_id", project_ids)
        .gte("created_at", since)
        .in_("status", ["proposed", "paid", "dismissed"])
        .execute()
        .data
        or []
    )
    return _summarize_orders(rows)


def billing_summary(
    freelancer_slack_id: str,
    *,
    period: str = "week",
) -> dict[str, Any]:
    supabase = get_supabase()
    projects = (
        supabase.table("projects")
        .select("id")
        .eq("freelancer_slack_id", freelancer_slack_id)
        .execute()
        .data
        or []
    )
    project_ids = [p["id"] for p in projects]
    return billing_summary_for_projects(project_ids, period=period)


def billing_summary_for_project(project_id: str) -> dict[str, Any]:
    supabase = get_supabase()
    rows = (
        supabase.table("change_orders")
        .select("status, estimated_cost, estimated_value, created_at")
        .eq("project_id", project_id)
        .in_("status", ["proposed", "paid", "dismissed"])
        .execute()
        .data
        or []
    )
    return _summarize_orders(rows)


def approved_additions_total(project_id: str) -> float:
    return billing_summary_for_project(project_id).get("approved", 0.0)
