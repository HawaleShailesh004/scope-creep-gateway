from datetime import datetime, timezone

from services.rts_search import _format_message_date, search_prior_mention


def test_format_message_date():
    # Slack ts for a known instant - use a round number
    ts = str(datetime(2026, 6, 12, 12, 0, 0, tzinfo=timezone.utc).timestamp())
    assert _format_message_date(ts) == "Jun 12, 2026"


def test_search_prior_mention_passes_after_ts(monkeypatch):
    captured = {}

    class FakeResp:
        def json(self):
            return {"ok": True, "results": {"messages": []}}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(json or {})
        return FakeResp()

    monkeypatch.setattr("services.rts_search.httpx.post", fake_post)

    search_prior_mention(
        "fake-token",
        channel_id="C123",
        query="blog section",
        before_ts="200.0",
        after_ts="100.0",
    )
    assert captured.get("after") == 100


def test_search_prior_mention_no_token_query_returns_false(monkeypatch):
    """Without a real API call, empty query short-circuits."""
    found, date = search_prior_mention(
        "fake-token",
        channel_id="C123",
        query="   ",
        before_ts="100.0",
    )
    assert found is False
    assert date is None
