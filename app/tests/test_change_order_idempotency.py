from services.change_orders import mark_change_order_paid, update_change_order_proposed


def test_update_change_order_proposed_only_from_flagged(monkeypatch):
    captured = {}

    class FakeResult:
        data = [{"id": "co-1", "status": "proposed"}]

    class FakeTable:
        def update(self, patch):
            captured["patch"] = patch
            return self

        def eq(self, column, value):
            captured.setdefault("filters", []).append((column, value))
            return self

        def execute(self):
            return FakeResult()

    class FakeSupabase:
        def table(self, name):
            return FakeTable()

    monkeypatch.setattr(
        "services.change_orders.get_supabase",
        lambda: FakeSupabase(),
    )

    result = update_change_order_proposed(
        "co-1",
        task_description="Blog section",
        estimated_cost=8000,
        timeline_impact_days=3,
    )
    assert result is not None
    assert captured["patch"]["status"] == "proposed"
    assert ("status", "flagged") in captured["filters"]


def test_mark_change_order_paid_only_from_proposed(monkeypatch):
    captured = {}

    class FakeResult:
        data = [{"id": "co-1", "status": "paid"}]

    class FakeTable:
        def update(self, patch):
            captured["patch"] = patch
            return self

        def eq(self, column, value):
            captured.setdefault("filters", []).append((column, value))
            return self

        def execute(self):
            return FakeResult()

    class FakeSupabase:
        def table(self, name):
            return FakeTable()

    monkeypatch.setattr(
        "services.change_orders.get_supabase",
        lambda: FakeSupabase(),
    )

    result = mark_change_order_paid("co-1")
    assert result is not None
    assert captured["patch"] == {"status": "paid"}
    assert ("status", "proposed") in captured["filters"]


def test_mark_change_order_paid_returns_none_when_not_proposed(monkeypatch):
    class FakeResult:
        data = []

    class FakeTable:
        def update(self, patch):
            return self

        def eq(self, column, value):
            return self

        def execute(self):
            return FakeResult()

    class FakeSupabase:
        def table(self, name):
            return FakeTable()

    monkeypatch.setattr(
        "services.change_orders.get_supabase",
        lambda: FakeSupabase(),
    )

    assert mark_change_order_paid("co-1") is None
