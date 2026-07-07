import pytest

from services.scope_health import (
    AbsorbedLike,
    ChangeOrderLike,
    HealthConfig,
    compute_scope_health,
)


def test_perfect_health_no_changes():
    result = compute_scope_health(
        [],
        budget_total=50000,
        created="2026-01-01",
        deadline="2026-02-01",
    )
    assert result.committed == 100
    assert result.projected == 100
    assert result.basis == "perfect"


def test_budget_penalty_paid_only_for_committed():
    cos = [
        ChangeOrderLike(estimated_cost=8000, timeline_impact_days=0, status="paid"),
        ChangeOrderLike(estimated_cost=4000, timeline_impact_days=0, status="proposed"),
    ]
    result = compute_scope_health(
        cos,
        budget_total=50000,
        created="2026-01-01",
        deadline="2026-02-01",
    )
    assert result.committed == 84  # 8000/50000 * 100 = 16 off
    assert result.projected == 76  # 12000/50000 * 100 = 24 off
    assert result.budget_penalty == 16.0


def test_time_penalty_uses_original_duration():
    cos = [
        ChangeOrderLike(estimated_cost=None, timeline_impact_days=15, status="paid"),
    ]
    result = compute_scope_health(
        cos,
        budget_total=None,
        created="2026-01-01",
        deadline="2026-02-01",  # 31 days
    )
    assert result.basis == "time_only"
    assert result.time_penalty == 30.0
    assert result.committed == 70


def test_absorbed_counts_at_half_weight():
    result = compute_scope_health(
        [],
        absorbed_items=[AbsorbedLike(estimated_value=10000)],
        budget_total=50000,
        created="2026-01-01",
        deadline="2026-02-01",
    )
    assert result.absorbed_penalty == 10.0  # 10000/50000*100*0.5
    assert result.committed == 90


def test_fallback_when_no_budget_or_deadline():
    cos = [
        ChangeOrderLike(estimated_cost=1000, timeline_impact_days=1, status="paid"),
        ChangeOrderLike(estimated_cost=1000, timeline_impact_days=1, status="proposed"),
    ]
    result = compute_scope_health(cos)
    assert result.basis == "fallback_count"
    assert result.committed == 88  # one paid CO => -12
    assert result.projected == 76  # two COs => -24


def test_dismissed_orders_ignored():
    cos = [
        ChangeOrderLike(estimated_cost=20000, timeline_impact_days=10, status="dismissed"),
    ]
    result = compute_scope_health(
        cos,
        budget_total=50000,
        created="2026-01-01",
        deadline="2026-02-01",
    )
    assert result.committed == 100


def test_caps_floor_health():
    cos = [
        ChangeOrderLike(estimated_cost=50000, timeline_impact_days=60, status="paid"),
    ]
    result = compute_scope_health(
        cos,
        absorbed_items=[AbsorbedLike(estimated_value=20000)],
        budget_total=50000,
        created="2026-01-01",
        deadline="2026-02-01",
        cfg=HealthConfig(),
    )
    assert result.budget_penalty == 40.0
    assert result.time_penalty == 30.0
    assert result.absorbed_penalty == 15.0
    assert result.committed == 15
