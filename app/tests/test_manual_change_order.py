from services.scope_warnings import create_manual_scope_flag, flag_already_exists


def test_create_manual_scope_flag_returns_id(monkeypatch):
    captured = {}

    class FakeResult:
        data = [{"id": "co-123"}]

    class FakeTable:
        def insert(self, row):
            captured["row"] = row
            return self

        def execute(self):
            return FakeResult()

    class FakeSupabase:
        def table(self, name):
            return FakeTable()

    monkeypatch.setattr(
        "services.scope_warnings.get_supabase",
        lambda: FakeSupabase(),
    )

    result = create_manual_scope_flag(
        project_id="proj-1",
        trigger_text="add a blog section",
        message_ts="1234.5678",
    )
    assert result == "co-123"
    assert captured["row"]["status"] == "flagged"
    assert captured["row"]["trigger_text"] == "add a blog section"


def test_flag_already_exists_true(monkeypatch):
    class FakeResult:
        data = [{"id": "existing"}]

    class FakeTable:
        def select(self, *_args):
            return self

        def eq(self, *_args):
            return self

        def limit(self, *_args):
            return self

        def execute(self):
            return FakeResult()

    class FakeSupabase:
        def table(self, name):
            return FakeTable()

    monkeypatch.setattr(
        "db.supabase_client.get_supabase",
        lambda: FakeSupabase(),
    )

    assert flag_already_exists("proj-1", "1234.5678") is True
