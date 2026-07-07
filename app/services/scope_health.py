"""
scope_health.py — value- and timeline-weighted Scope Health.

Replaces the flat "-12 per change order" model. Health now reflects real scope
pressure on the project:

    money added   (billed change orders vs original budget)
  + time added    (extra days vs the ORIGINAL project duration, not remaining)
  + unbilled creep (absorbed goodwill work — the creep that actually costs the
                    freelancer, which the old formula ignored entirely)

KEY DECISIONS (and why):

1. Time is anchored to ORIGINAL duration (created -> original deadline), NOT
   days-until-deadline. Using remaining time makes health silently decay as the
   deadline nears and explodes/negatives past it. Original duration is a fixed,
   meaningful denominator: "how much did we add relative to the deal we struck".

2. Everything is null-guarded. Budget and deadline are optional in setup. A
   missing component is DROPPED (its penalty is 0) rather than crashing or
   silently reading as perfect health. If nothing is computable, we fall back to
   a gentle count-based penalty so health still moves.

3. Absorbed (let-it-slide) work counts against health, at a discount. Unbilled
   scope creep is arguably the WORST for the freelancer's economics, so a project
   where creep was absorbed is LESS healthy than one where it was billed. We
   weight it at `absorbed_weight` (default 0.5) of its value — present, but not
   dominant, because absorbing small goodwill is a legitimate choice.

4. Committed vs projected. `status='paid'` (and optionally 'proposed') COs are
   "committed". We expose both a committed health and a projected health so a
   proposed-but-unapproved CO doesn't permanently dent the headline number.

5. Caps are explicit and documented. Max penalties: budget 40, time 30,
   absorbed 15 => health floors at 15 when all rails are hit. Raise caps if you
   want 0% reachable. This is a deliberate choice, not an accident of the maths.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

@dataclass
class ChangeOrderLike:
    estimated_cost: Optional[float]
    timeline_impact_days: Optional[float]
    status: str  # 'flagged' | 'proposed' | 'paid' | 'dismissed'


@dataclass
class AbsorbedLike:
    estimated_value: Optional[float]


@dataclass
class HealthConfig:
    budget_cap: float = 40.0       # max points from money creep
    time_cap: float = 30.0         # max points from schedule creep
    absorbed_cap: float = 15.0     # max points from unbilled goodwill
    absorbed_weight: float = 0.5   # absorbed value counts at half toward penalty
    # Statuses considered "committed" scope change for the headline number.
    committed_statuses: tuple = ("paid",)
    # Statuses considered for the "projected" number (headline + pending).
    projected_statuses: tuple = ("paid", "proposed")
    # Fallback when neither budget nor deadline is known: points per committed CO.
    fallback_points_per_co: float = 12.0


@dataclass
class HealthResult:
    committed: int          # headline health (0-100), based on paid COs
    projected: int          # health including proposed COs (0-100)
    budget_penalty: float
    time_penalty: float
    absorbed_penalty: float
    basis: str              # "weighted" | "time_only" | "budget_only" |
                            # "fallback_count" | "perfect"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_date(d) -> Optional[date]:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    # accept ISO strings
    try:
        return datetime.fromisoformat(str(d)).date()
    except (ValueError, TypeError):
        return None


def _original_duration_days(created, deadline) -> Optional[int]:
    c = _to_date(created)
    d = _to_date(deadline)
    if c is None or d is None:
        return None
    days = (d - c).days
    # Guard zero/negative (same-day or misconfigured deadline).
    return days if days > 0 else None


def _sum_cost(cos: Iterable[ChangeOrderLike], statuses) -> float:
    return sum((co.estimated_cost or 0.0) for co in cos if co.status in statuses)


def _sum_days(cos: Iterable[ChangeOrderLike], statuses) -> float:
    return sum((co.timeline_impact_days or 0.0) for co in cos if co.status in statuses)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _compute_for_statuses(
    cos: list[ChangeOrderLike],
    absorbed: list[AbsorbedLike],
    budget_total: Optional[float],
    created,
    deadline,
    statuses,
    cfg: HealthConfig,
) -> tuple[int, float, float, float, str]:
    """Returns (health, budget_penalty, time_penalty, absorbed_penalty, basis)."""

    creep_cost = _sum_cost(cos, statuses)
    creep_days = _sum_days(cos, statuses)
    absorbed_value = sum((a.estimated_value or 0.0) for a in absorbed)

    have_budget = budget_total is not None and budget_total > 0
    duration = _original_duration_days(created, deadline)
    have_time = duration is not None

    budget_penalty = 0.0
    time_penalty = 0.0
    absorbed_penalty = 0.0

    if have_budget:
        budget_penalty = min(cfg.budget_cap, (creep_cost / budget_total) * 100.0)
        # Absorbed goodwill is measured against the same budget, discounted.
        if absorbed_value > 0:
            absorbed_penalty = min(
                cfg.absorbed_cap,
                (absorbed_value / budget_total) * 100.0 * cfg.absorbed_weight,
            )

    if have_time:
        time_penalty = min(cfg.time_cap, (creep_days / duration) * 100.0)

    # Decide basis + fallback.
    if have_budget and have_time:
        basis = "weighted"
    elif have_time and not have_budget:
        basis = "time_only"
    elif have_budget and not have_time:
        basis = "budget_only"
    else:
        # Nothing computable — fall back to a gentle count-based penalty so the
        # number still reflects that scope changed.
        n = sum(1 for co in cos if co.status in statuses)
        fallback_penalty = min(
            cfg.budget_cap + cfg.time_cap,
            n * cfg.fallback_points_per_co,
        )
        health = max(0, round(100 - fallback_penalty))
        return health, 0.0, 0.0, 0.0, "fallback_count"

    total_penalty = budget_penalty + time_penalty + absorbed_penalty
    health = max(0, round(100 - total_penalty))
    if total_penalty == 0:
        basis = "perfect"
    return health, budget_penalty, time_penalty, absorbed_penalty, basis


def compute_scope_health(
    change_orders: list[ChangeOrderLike],
    absorbed_items: Optional[list[AbsorbedLike]] = None,
    budget_total: Optional[float] = None,
    created=None,
    deadline=None,
    cfg: Optional[HealthConfig] = None,
) -> HealthResult:
    """
    Compute Scope Health.

    Args:
        change_orders: all COs for the project (any status; filtered internally).
        absorbed_items: let-it-slide items (unbilled goodwill). Optional.
        budget_total:   original project budget. Optional (may be None/0).
        created:        project creation date (date/datetime/ISO str).
        deadline:       ORIGINAL deadline (date/datetime/ISO str).
        cfg:            HealthConfig overrides.

    Returns:
        HealthResult with committed (headline) and projected health, the penalty
        breakdown, and the basis used (for canvas copy / debugging).

    Notes:
        - Time penalty uses ORIGINAL duration (created -> deadline), so health
          does not drift as the deadline approaches.
        - Absorbed items count against BOTH committed and projected health
          (unbilled creep is real pressure regardless of CO status).
        - Fully null-safe: missing budget/deadline degrade gracefully.
    """
    cfg = cfg or HealthConfig()
    absorbed = absorbed_items or []

    committed, b_pen, t_pen, a_pen, basis = _compute_for_statuses(
        change_orders, absorbed, budget_total, created, deadline,
        cfg.committed_statuses, cfg,
    )
    projected, *_ = _compute_for_statuses(
        change_orders, absorbed, budget_total, created, deadline,
        cfg.projected_statuses, cfg,
    )

    return HealthResult(
        committed=committed,
        projected=projected,
        budget_penalty=round(b_pen, 1),
        time_penalty=round(t_pen, 1),
        absorbed_penalty=round(a_pen, 1),
        basis=basis,
    )


# ---------------------------------------------------------------------------
# Presentation helpers (for canvas copy)
# ---------------------------------------------------------------------------

def health_emoji(health: int) -> str:
    if health >= 85:
        return "🟢"
    if health >= 60:
        return "🟡"
    return "🔴"


def health_summary_line(result: HealthResult) -> str:
    """One-line canvas summary. Uses committed (headline) health."""
    emoji = health_emoji(result.committed)
    line = f"**Scope Health:** {emoji} {result.committed}%"
    if result.projected != result.committed:
        line += f"  _(projected {result.projected}% with pending change orders)_"
    return line


def health_breakdown_lines(result: HealthResult) -> list[str]:
    """Optional detailed breakdown for the canvas (separate bars/numbers)."""
    lines = []
    if result.basis in ("weighted", "budget_only"):
        lines.append(f"• Budget impact: −{result.budget_penalty} pts")
    if result.basis in ("weighted", "time_only"):
        lines.append(f"• Timeline impact: −{result.time_penalty} pts")
    if result.absorbed_penalty > 0:
        lines.append(f"• Unbilled goodwill: −{result.absorbed_penalty} pts")
    if result.basis == "fallback_count":
        lines.append("• Based on number of change orders (no budget/deadline set)")
    return lines
