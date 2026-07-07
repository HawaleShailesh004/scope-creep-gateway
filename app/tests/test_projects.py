from services.projects import is_analysis_allowed


def test_analysis_blocked_without_disclosure():
    assert not is_analysis_allowed({"disclosure_ts": None, "classification_enabled": True})
    assert not is_analysis_allowed({"classification_enabled": True})


def test_analysis_blocked_when_disabled():
    assert not is_analysis_allowed(
        {"disclosure_ts": "123.456", "classification_enabled": False}
    )


def test_analysis_allowed_when_disclosed_and_enabled():
    assert is_analysis_allowed(
        {"disclosure_ts": "123.456", "classification_enabled": True}
    )


def test_analysis_allowed_when_classification_enabled_null():
    assert is_analysis_allowed({"disclosure_ts": "123.456"})
