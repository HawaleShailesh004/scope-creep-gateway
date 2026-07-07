from __future__ import annotations

from datetime import date
from typing import Any

from db.supabase_client import get_supabase
from services.brief_template import format_change_log_entry
from services.scope_health import (
    AbsorbedLike,
    ChangeOrderLike,
    HealthResult,
    compute_scope_health as compute_weighted_scope_health,
)


def get_change_order(change_order_id: str) -> dict | None:
    supabase = get_supabase()
    result = (
        supabase.table("change_orders")
        .select("*")
        .eq("id", change_order_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def list_project_change_orders(project_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    result = (
        supabase.table("change_orders")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at")
        .execute()
    )
    return result.data or []


def proposed_cost_total(project_id: str) -> float:
    orders = list_project_change_orders(project_id)
    total = 0.0
    for order in orders:
        if order.get("status") in ("proposed", "paid") and order.get("estimated_cost"):
            total += float(order["estimated_cost"])
    return total


def change_order_number(project_id: str, change_order_id: str) -> int:
    orders = [
        o
        for o in list_project_change_orders(project_id)
        if o.get("status") in ("proposed", "paid")
    ]
    for idx, order in enumerate(orders, start=1):
        if order["id"] == change_order_id:
            return idx
    return len(orders) + 1


def update_change_order_proposed(
    change_order_id: str,
    *,
    task_description: str,
    estimated_cost: float,
    timeline_impact_days: int,
) -> dict | None:
    supabase = get_supabase()
    patch: dict[str, Any] = {
        "task_description": task_description,
        "estimated_cost": estimated_cost,
        "timeline_impact_days": timeline_impact_days,
        "status": "proposed",
    }
    result = (
        supabase.table("change_orders")
        .update(patch)
        .eq("id", change_order_id)
        .eq("status", "flagged")
        .execute()
    )
    return result.data[0] if result.data else None


def mark_change_order_paid(change_order_id: str) -> dict | None:
    supabase = get_supabase()
    result = (
        supabase.table("change_orders")
        .update({"status": "paid"})
        .eq("id", change_order_id)
        .eq("status", "proposed")
        .execute()
    )
    return result.data[0] if result.data else None


def build_change_log_entries(
    change_orders: list[dict[str, Any]],
    *,
    currency: str = "INR",
) -> list[str]:
    entries = []
    for order in change_orders:
        if order.get("status") not in ("proposed", "paid"):
            continue
        label = order.get("task_description") or order.get("trigger_text") or "Change"
        created = order.get("created_at", "")[:10] or None
        entries.append(
            format_change_log_entry(
                label=label.split(".")[0][:60],
                cost=order.get("estimated_cost"),
                days=order.get("timeline_impact_days"),
                status=order.get("status", "proposed"),
                currency=currency,
                entry_date=created,
            )
        )
    return entries


def list_absorbed_items(project_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    result = (
        supabase.table("absorbed_items")
        .select("estimated_value")
        .eq("project_id", project_id)
        .execute()
    )
    return result.data or []


def _to_change_order_likes(orders: list[dict[str, Any]]) -> list[ChangeOrderLike]:
    return [
        ChangeOrderLike(
            estimated_cost=order.get("estimated_cost"),
            timeline_impact_days=order.get("timeline_impact_days"),
            status=order.get("status") or "flagged",
        )
        for order in orders
    ]


def compute_project_scope_health(
    project: dict[str, Any],
    change_orders: list[dict[str, Any]],
    absorbed_items: list[dict[str, Any]] | None = None,
) -> HealthResult:
    """Value/timeline/absorbed-weighted Scope Health for a project."""
    absorbed = [
        AbsorbedLike(estimated_value=row.get("estimated_value"))
        for row in (absorbed_items or [])
    ]
    return compute_weighted_scope_health(
        _to_change_order_likes(change_orders),
        absorbed_items=absorbed,
        budget_total=project.get("budget_total"),
        created=project.get("created_at"),
        deadline=project.get("deadline"),
    )


def compute_scope_health(change_orders: list[dict[str, Any]]) -> int:
    """Legacy flat fallback when project context is unavailable."""
    result = compute_weighted_scope_health(_to_change_order_likes(change_orders))
    return result.committed


def save_project_scope_health(project_id: str, scope_health: int) -> None:
    supabase = get_supabase()
    supabase.table("projects").update({"scope_health": scope_health}).eq(
        "id", project_id
    ).execute()
