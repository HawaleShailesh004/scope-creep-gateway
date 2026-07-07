from __future__ import annotations

from datetime import date
from decimal import Decimal

from services.scope_canvas import CanvasModel, Deliverable, build_full_canvas_markdown


def parse_deliverables(raw: str) -> list[str]:
    lines = [line.strip() for line in raw.splitlines()]
    return [line for line in lines if line]


def format_budget(amount: Decimal | float | int | None, currency: str = "INR") -> str:
    if amount is None:
        return "-"
    symbol = "₹" if currency == "INR" else f"{currency} "
    if currency == "INR":
        return f"{symbol}{amount:,.0f}"
    return f"{symbol}{amount:,.2f}"


def format_deadline(deadline: date | str | None) -> str:
    if deadline is None:
        return "-"
    if isinstance(deadline, str):
        return deadline
    return deadline.isoformat()


def health_indicator(scope_health: int) -> str:
    if scope_health >= 85:
        return "🟢"
    if scope_health >= 60:
        return "🟡"
    return "🔴"


def format_change_log_entry(
    *,
    label: str,
    cost: Decimal | float | int | None,
    days: int | None,
    status: str,
    currency: str = "INR",
    entry_date: date | str | None = None,
) -> str:
    when = format_deadline(entry_date) if entry_date else date.today().isoformat()
    try:
        parsed = date.fromisoformat(str(when))
        when = parsed.strftime("%b %d")
    except ValueError:
        pass
    cost_part = format_budget(cost, currency) if cost is not None else "-"
    days_part = f"+{days} days" if days is not None else "-"
    return f"- {when} - {label} ({cost_part}, {days_part}) - {status}"


def build_canvas_markdown(
    *,
    project_name: str,
    deliverables: list[str],
    budget_total: Decimal | float | int | None,
    deadline: date | str | None,
    currency: str = "INR",
    scope_health: int = 100,
    health_lines: list[str] | None = None,
    change_log_entries: list[str] | None = None,
    freelancer_id: str = "",
) -> str:
    """Backward-compatible wrapper around the scope canvas builder."""
    budget = float(budget_total) if budget_total is not None else None
    deadline_str = format_deadline(deadline) if deadline != "-" else None
    if deadline_str == "-":
        deadline_str = None

    model = CanvasModel(
        project_name=project_name,
        currency=currency,
        budget_total=budget,
        deadline=deadline_str,
        health_committed=scope_health,
        health_projected=scope_health,
        budget_used_pct=0.0,
        timeline_used_pct=0.0,
        deliverables=[Deliverable(description=d, origin="setup") for d in deliverables],
        freelancer_id=freelancer_id,
    )
    return build_full_canvas_markdown(model)


def build_canvas_markdown_for_project(project: dict, **kwargs) -> str:
    from services.canvas_model import build_canvas_markdown_from_project

    return build_canvas_markdown_from_project(project, **kwargs)
