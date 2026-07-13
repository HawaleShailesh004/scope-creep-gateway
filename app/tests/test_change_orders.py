from listeners.views.change_order_card import (
    build_change_order_card_blocks,
    build_client_payment_ephemeral_blocks,
)
from services.brief_template import health_indicator
from services.change_orders import compute_scope_health


def test_compute_scope_health_fallback_without_project_context():
    orders = [{"status": "proposed"}, {"status": "paid"}]
    assert compute_scope_health(orders) == 88  # committed: one paid CO => -12


def test_compute_scope_health_ignores_dismissed():
    orders = [{"status": "dismissed"}, {"status": "flagged"}]
    assert compute_scope_health(orders) == 100


def test_health_indicator_thresholds():
    assert health_indicator(100) == "🟢"
    assert health_indicator(85) == "🟢"
    assert health_indicator(84) == "🟡"
    assert health_indicator(60) == "🟡"
    assert health_indicator(59) == "🔴"


def test_public_change_order_card_has_no_payment_buttons(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    blocks = build_change_order_card_blocks(
        order_number=1,
        title="Add blog section",
        task_description="Blog/content section not in original brief.",
        estimated_cost=8000,
        timeline_impact_days=3,
        budget_total=50000,
        currency="INR",
        change_order_id="co-1",
        channel_id="C123",
        message_ts="1.0",
        thread_ts="0.9",
        project_id="p1",
        include_payment=False,
        include_draft_reply=False,
    )
    assert len(blocks) == 1
    assert "Awaiting client approval" in blocks[0]["text"]["text"]


def test_client_ephemeral_has_pay_and_simulate(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    blocks = build_client_payment_ephemeral_blocks(
        order_number=1,
        title="Add blog section",
        change_order_id="co-1",
        channel_id="C123",
        message_ts="1.0",
        thread_ts="0.9",
    )
    actions = blocks[1]["elements"]
    assert actions[0]["action_id"] == "approve_pay_link"
    assert actions[1]["action_id"] == "simulate_payment"


def test_client_ephemeral_hides_simulate_when_demo_off(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    blocks = build_client_payment_ephemeral_blocks(
        order_number=1,
        title="Add blog section",
        change_order_id="co-1",
        channel_id="C123",
        message_ts="1.0",
        thread_ts="0.9",
    )
    actions = blocks[1]["elements"]
    assert len(actions) == 1
    assert actions[0]["action_id"] == "approve_pay_link"


def test_change_order_card_paid_has_no_actions():
    blocks = build_change_order_card_blocks(
        order_number=1,
        title="Add blog",
        task_description="Blog section",
        estimated_cost=8000,
        timeline_impact_days=3,
        budget_total=50000,
        currency="INR",
        change_order_id="co-1",
        channel_id="C123",
        message_ts="1.0",
        thread_ts="0.9",
        project_id="p1",
        paid=True,
    )
    assert len(blocks) == 1
    assert "Paid" in blocks[0]["text"]["text"]
