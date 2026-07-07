"""
scope_canvas.py — builds and updates the project Scope Canvas markdown.

Canvas layout (top → bottom):
    1. Title + health status
    2. At-a-glance bars (budget / timeline)
    3. In scope (original deliverables)
    4. Added & agreed (paid change orders)
    5. Pending your approval (proposed COs)
    6. Change log (audit trail)
    7. Footer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Stable section anchors for canvases.sections.lookup (must match headings below).
ANCHOR_SCOPE_HEALTH = "Scope Health"
ANCHOR_AT_A_GLANCE = "At a glance"
ANCHOR_IN_SCOPE = "In scope"
ANCHOR_ADDED = "Added & agreed"
ANCHOR_PENDING = "Pending your approval"
ANCHOR_EXCLUSIONS = "Explicitly out of scope"
ANCHOR_CHANGE_LOG = "Change log"


@dataclass
class Deliverable:
    description: str
    origin: str = "setup"  # setup | change_order


@dataclass
class ChangeLogEntry:
    when: str
    summary: str
    cost: Optional[float]
    days: Optional[int]
    status: str  # proposed | paid | dismissed


@dataclass
class CanvasModel:
    project_name: str
    currency: str
    budget_total: Optional[float]
    deadline: Optional[str]
    health_committed: int
    health_projected: int
    budget_used_pct: float
    timeline_used_pct: float
    deliverables: list[Deliverable] = field(default_factory=list)
    pending: list[ChangeLogEntry] = field(default_factory=list)
    change_log: list[ChangeLogEntry] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    approved_additions_value: float | None = None
    freelancer_id: str = ""


def _emoji(health: int) -> str:
    return "🟢" if health >= 85 else "🟡" if health >= 60 else "🔴"


def _bar(pct: float, width: int = 20) -> str:
    filled = max(0, min(width, round((pct / 100.0) * width)))
    return "█" * filled + "░" * (width - filled)


def _money(currency: str, amount: Optional[float]) -> str:
    if amount is None:
        return "—"
    sym = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(currency, "")
    if amount == int(amount):
        return f"{sym}{int(amount):,}"
    return f"{sym}{amount:,.2f}"


def _status_block(m: CanvasModel) -> str:
    emoji = _emoji(m.health_committed)
    line = f"# 🛡️ {m.project_name}\n\n**Scope Health:** {emoji} {m.health_committed}%"
    if m.health_projected != m.health_committed:
        line += f"  _(projected {m.health_projected}% with pending items)_"
    return line


def _bars_block(m: CanvasModel) -> str:
    lines = ["## At a glance", ""]
    if m.budget_total:
        lines.append(
            f"**Budget**  `{_bar(m.budget_used_pct)}`  "
            f"{_money(m.currency, m.budget_total)} agreed"
        )
    if m.timeline_used_pct is not None:
        lines.append(
            f"**Timeline**  `{_bar(m.timeline_used_pct)}`  "
            f"{'+' if m.timeline_used_pct else ''}added vs plan"
        )
    if len(lines) == 2:
        lines.append("_Budget and deadline not set — health uses change count._")
    return "\n".join(lines)


def _in_scope_block(m: CanvasModel) -> str:
    original = [d for d in m.deliverables if d.origin == "setup"]
    lines = ["## In scope", ""]
    if original:
        lines += [f"- {d.description}" for d in original]
    else:
        lines.append("_No deliverables recorded._")
    return "\n".join(lines)


def _exclusions_block(m: CanvasModel) -> str:
    lines = ["## Explicitly out of scope", ""]
    if m.exclusions:
        lines += [f"- {item}" for item in m.exclusions]
    else:
        lines.append("_None noted at kickoff._")
    return "\n".join(lines)


def _added_block(m: CanvasModel) -> str:
    added = [d for d in m.deliverables if d.origin == "change_order"]
    lines = ["## Added & agreed", ""]
    if added:
        lines += [f"- {d.description}  _(added via change order)_" for d in added]
    else:
        lines.append("_None yet._")
    if m.approved_additions_value:
        from services.brief_template import format_budget

        lines.append("")
        lines.append(
            f"**Approved additions:** {format_budget(m.approved_additions_value, m.currency)}"
        )
    return "\n".join(lines)


def _pending_block(m: CanvasModel) -> str:
    lines = ["## Pending your approval", ""]
    if m.pending:
        lines.append("| Item | Cost | Timeline |")
        lines.append("|------|------|----------|")
        for p in m.pending:
            cost = _money(m.currency, p.cost)
            days = f"+{p.days} days" if p.days else "—"
            lines.append(f"| {p.summary} | {cost} | {days} |")
    else:
        lines.append("_Nothing pending._")
    return "\n".join(lines)


def _change_log_block(m: CanvasModel) -> str:
    lines = ["## Change log", ""]
    if m.change_log:
        lines.append("| Date | Change | Cost | Timeline | Status |")
        lines.append("|------|--------|------|----------|--------|")
        for e in m.change_log:
            cost = _money(m.currency, e.cost)
            days = f"+{e.days}d" if e.days else "—"
            status = {
                "paid": "✅ Agreed",
                "proposed": "⏳ Pending",
                "dismissed": "— Withdrawn",
            }.get(e.status, e.status)
            lines.append(f"| {e.when} | {e.summary} | {cost} | {days} | {status} |")
    else:
        lines.append("_No changes yet — right on scope._")
    return "\n".join(lines)


def _footer_block(m: CanvasModel) -> str:
    who = f"<@{m.freelancer_id}>" if m.freelancer_id else "the freelancer"
    return (
        "---\n"
        f"_This scope record is kept up to date automatically. Questions about "
        f"anything here? Just ask {who}._"
    )


def build_full_canvas_markdown(m: CanvasModel) -> str:
    blocks = [
        _status_block(m),
        _bars_block(m),
        _in_scope_block(m),
        _exclusions_block(m),
        _added_block(m),
        _pending_block(m),
        _change_log_block(m),
        _footer_block(m),
    ]
    return "\n\n".join(blocks)


def status_section_markdown(m: CanvasModel) -> str:
    """Replace status + at-a-glance blocks after a health change."""
    return _status_block(m) + "\n\n" + _bars_block(m)


def section_markdown(m: CanvasModel, anchor: str) -> str:
    """Markdown for one named section (for targeted canvases.edit replace)."""
    builders = {
        ANCHOR_SCOPE_HEALTH: lambda: _status_block(m),
        ANCHOR_AT_A_GLANCE: lambda: _bars_block(m),
        ANCHOR_IN_SCOPE: lambda: _in_scope_block(m),
        ANCHOR_EXCLUSIONS: lambda: _exclusions_block(m),
        ANCHOR_ADDED: lambda: _added_block(m),
        ANCHOR_PENDING: lambda: _pending_block(m),
        ANCHOR_CHANGE_LOG: lambda: _change_log_block(m),
    }
    if anchor == ANCHOR_SCOPE_HEALTH:
        return _status_block(m)
    builder = builders.get(anchor)
    if not builder:
        raise ValueError(f"Unknown canvas section anchor: {anchor}")
    return builder()


def change_log_row_markdown(e: ChangeLogEntry, currency: str) -> str:
    cost = _money(currency, e.cost)
    days = f"+{e.days}d" if e.days else "—"
    status = {
        "paid": "✅ Agreed",
        "proposed": "⏳ Pending",
        "dismissed": "— Withdrawn",
    }.get(e.status, e.status)
    return f"| {e.when} | {e.summary} | {cost} | {days} | {status} |"
