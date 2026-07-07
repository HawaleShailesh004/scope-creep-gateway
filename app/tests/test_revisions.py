from services.revisions import revision_limit_breached


def test_revision_limit_not_breached_when_under(monkeypatch):
    monkeypatch.setattr("services.revisions.count_revisions", lambda _id: 1)
    deliverable = {"id": "d1", "revision_limit": 2}
    assert not revision_limit_breached(deliverable)


def test_revision_limit_breached_at_limit(monkeypatch):
    monkeypatch.setattr("services.revisions.count_revisions", lambda _id: 2)
    deliverable = {"id": "d1", "revision_limit": 2}
    assert revision_limit_breached(deliverable)


def test_revision_limit_not_breached_when_unlimited(monkeypatch):
    monkeypatch.setattr("services.revisions.count_revisions", lambda _id: 99)
    deliverable = {"id": "d1", "revision_limit": None}
    assert not revision_limit_breached(deliverable)
