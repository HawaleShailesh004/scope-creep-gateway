from services.absorbed import (
    ABSORB_COUNT_THRESHOLD,
    ABSORB_VALUE_THRESHOLD,
    running_total,
    threshold_crossed,
)


def test_threshold_crossed_by_count():
    totals = {"count": ABSORB_COUNT_THRESHOLD, "total_value": 0}
    assert threshold_crossed(totals)


def test_threshold_crossed_by_value():
    totals = {"count": 1, "total_value": ABSORB_VALUE_THRESHOLD}
    assert threshold_crossed(totals)


def test_threshold_not_crossed():
    totals = {"count": 1, "total_value": 500}
    assert not threshold_crossed(totals)


def test_running_total_empty_without_scope():
    assert running_total() == {
        "count": 0,
        "total_value": 0.0,
        "manual_count": 0,
        "auto_count": 0,
    }
