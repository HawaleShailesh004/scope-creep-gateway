class _FakeQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def lt(self, *args, **kwargs):
        return self

    def not_(self):
        return self

    def is_(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def execute(self):
        return type("R", (), {"data": self._data, "count": len(self._data)})()


class _FakeSupabase:
    def __init__(self, projects, change_orders, absorbed):
        self._projects = projects
        self._change_orders = change_orders
        self._absorbed = absorbed
        self.updates = []

    def table(self, name):
        if name == "projects":
            return _FakeQuery(self._projects)
        if name == "change_orders":
            return _ChangeOrderTable(self._change_orders, self.updates)
        if name == "absorbed_items":
            return _AbsorbedTable(self._absorbed, self.updates)
        raise KeyError(name)


class _ChangeOrderTable:
    def __init__(self, rows, updates):
        self._rows = rows
        self._updates = updates
        self._filters = {}

    @property
    def not_(self):
        return self

    def select(self, *args, **kwargs):
        return self

    def eq(self, field, value):
        self._filters[field] = value
        return self

    def in_(self, field, values):
        self._filters["status_in"] = values
        return self

    def lt(self, field, value):
        self._filters["lt"] = (field, value)
        return self

    def is_(self, field, value):
        self._filters["not_null"] = field
        return self

    def update(self, patch):
        self._patch = patch
        return self

    def execute(self):
        matched = []
        for row in self._rows:
            if self._filters.get("project_id") and row["project_id"] != self._filters["project_id"]:
                continue
            if "status_in" in self._filters and row.get("status") not in self._filters["status_in"]:
                continue
            if row.get("trigger_text") is None:
                continue
            matched.append(row)
        for row in matched:
            row["trigger_text"] = None
            self._updates.append(("change_orders", row["id"]))
        return type("R", (), {"data": matched})()


class _AbsorbedTable(_ChangeOrderTable):
    pass


def test_purge_nulls_resolved_change_order_text(monkeypatch):
    from services import retention

    rows = [
        {
            "id": "co1",
            "project_id": "p1",
            "status": "paid",
            "trigger_text": "please add blog",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    ]
    fake = _FakeSupabase(
        projects=[{"id": "p1", "retention_days": 30}],
        change_orders=rows,
        absorbed=[],
    )
    monkeypatch.setattr(retention, "get_supabase", lambda: fake)

    counts = retention.purge_expired_text()
    assert counts["change_orders"] >= 1
    assert rows[0]["trigger_text"] is None
