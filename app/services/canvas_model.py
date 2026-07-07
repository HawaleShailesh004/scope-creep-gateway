from __future__ import annotations

from datetime import date, datetime
from typing import Any

from services.billing_status import approved_additions_total
from services.deliverables import load_exclusions
from services.deliverables import load_effective_deliverables, sync_paid_change_orders_to_deliverables
from services.scope_canvas import CanvasModel, ChangeLogEntry, Deliverable, build_full_canvas_markdown
from services.scope_health import AbsorbedLike, HealthResult, compute_scope_health
from services.change_orders import _to_change_order_likes


def _format_when(raw: str | None) -> str:
    if not raw:
        return date.today().strftime("%b %d")
    try:
        if "T" in raw:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.strftime("%b %d")
        parsed = date.fromisoformat(raw[:10])
        return parsed.strftime("%b %d")
    except (ValueError, TypeError):
        return raw[:10] if raw else "—"


def _summary(order: dict[str, Any]) -> str:
    label = order.get("task_description") or order.get("trigger_text") or "Change"
    return label.split(".")[0][:60]


def _order_to_log_entry(order: dict[str, Any]) -> ChangeLogEntry:
    cost = order.get("estimated_cost")
    days = order.get("timeline_impact_days")
    return ChangeLogEntry(
        when=_format_when(order.get("created_at")),
        summary=_summary(order),
        cost=float(cost) if cost is not None else None,
        days=int(days) if days is not None else None,
        status=order.get("status") or "proposed",
    )


def _budget_used_pct(
    change_orders: list[dict[str, Any]],
    budget_total: float | None,
) -> float:
    if not budget_total or budget_total <= 0:
        return 0.0
    total = sum(
        float(o.get("estimated_cost") or 0)
        for o in change_orders
        if o.get("status") in ("paid", "proposed")
    )
    return min(100.0, (total / budget_total) * 100.0)


def _timeline_used_pct(
    change_orders: list[dict[str, Any]],
    created,
    deadline,
) -> float:
    from services.scope_health import _original_duration_days

    duration = _original_duration_days(created, deadline)
    if not duration:
        return 0.0
    days = sum(
        float(o.get("timeline_impact_days") or 0)
        for o in change_orders
        if o.get("status") in ("paid", "proposed")
    )
    return min(100.0, (days / duration) * 100.0)


def build_canvas_model(
    project: dict[str, Any],
    *,
    deliverable_rows: list[dict[str, Any]] | None = None,
    change_orders: list[dict[str, Any]] | None = None,
    health: HealthResult | None = None,
) -> CanvasModel:
    project_id = project["id"]
    sync_paid_change_orders_to_deliverables(project_id)

    if deliverable_rows is None:
        deliverable_rows = load_effective_deliverables(project_id)
    if change_orders is None:
        change_orders = list_project_change_orders(project_id)
    if health is None:
        absorbed = list_absorbed_items(project_id)
        health = compute_scope_health(
            _to_change_order_likes(change_orders),
            absorbed_items=[
                AbsorbedLike(estimated_value=r.get("estimated_value")) for r in absorbed
            ],
            budget_total=project.get("budget_total"),
            created=project.get("created_at"),
            deadline=project.get("deadline"),
        )

    currency = project.get("currency") or "INR"
    budget_total = project.get("budget_total")
    if budget_total is not None:
        budget_total = float(budget_total)

    deliverables = [
        Deliverable(
            description=row.get("description") or "",
            origin=row.get("origin") or "setup",
        )
        for row in deliverable_rows
        if row.get("description")
    ]

    log_orders = [
        o for o in change_orders if o.get("status") in ("proposed", "paid", "dismissed")
    ]
    pending = [_order_to_log_entry(o) for o in change_orders if o.get("status") == "proposed"]

    return CanvasModel(
        project_name=project.get("project_name") or "Project",
        currency=currency,
        budget_total=budget_total,
        deadline=project.get("deadline"),
        health_committed=health.committed,
        health_projected=health.projected,
        budget_used_pct=_budget_used_pct(change_orders, budget_total),
        timeline_used_pct=_timeline_used_pct(
            change_orders, project.get("created_at"), project.get("deadline")
        ),
        deliverables=deliverables,
        pending=pending,
        change_log=[_order_to_log_entry(o) for o in log_orders],
        exclusions=load_exclusions(project_id),
        approved_additions_value=approved_additions_total(project_id) or None,
        freelancer_id=project.get("freelancer_slack_id") or "",
    )


def build_canvas_markdown_from_project(
    project: dict[str, Any],
    *,
    deliverable_rows: list[dict[str, Any]] | None = None,
    change_orders: list[dict[str, Any]] | None = None,
    health: HealthResult | None = None,
) -> str:
    model = build_canvas_model(
        project,
        deliverable_rows=deliverable_rows,
        change_orders=change_orders,
        health=health,
    )
    return build_full_canvas_markdown(model)
