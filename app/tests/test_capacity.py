"""Tests for v3 capacity rollups."""

from services.capacity import capacity_pct_of_week


def test_capacity_pct_of_week():
    assert capacity_pct_of_week(20) == 50
    assert capacity_pct_of_week(40) == 100
