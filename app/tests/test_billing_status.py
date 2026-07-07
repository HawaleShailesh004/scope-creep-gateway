"""Tests for billing status rollups."""

from services.billing_status import _summarize_orders


def test_summarize_orders_mixed_statuses():
    orders = [
        {"status": "proposed", "estimated_cost": 10000},
        {"status": "paid", "estimated_cost": 8000},
        {"status": "dismissed", "estimated_cost": 2000},
    ]
    result = _summarize_orders(orders)
    assert result["billed"] == 18000
    assert result["approved"] == 8000
    assert result["pending"] == 10000
    assert result["withdrawn"] == 2000
