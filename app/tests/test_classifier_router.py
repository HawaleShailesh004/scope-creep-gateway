from services.classifier_router import route_classification


def test_trivial_out_of_scope_warns():
    decision = route_classification(
        classification={
            "verdict": "OUT_OF_SCOPE",
            "confidence": 0.95,
            "size": "trivial",
        },
        project_id="p1",
        deliverables=[],
    )
    assert decision.action == "warn"


def test_small_out_of_scope_warns():
    decision = route_classification(
        classification={
            "verdict": "OUT_OF_SCOPE",
            "confidence": 0.9,
            "size": "small",
        },
        project_id="p1",
        deliverables=[],
    )
    assert decision.action == "warn"


def test_warn_significant_out_of_scope():
    decision = route_classification(
        classification={
            "verdict": "OUT_OF_SCOPE",
            "confidence": 0.85,
            "size": "significant",
        },
        project_id="p1",
        deliverables=[],
    )
    assert decision.action == "warn"


def test_silent_ambiguous():
    decision = route_classification(
        classification={"verdict": "AMBIGUOUS", "confidence": 0.5},
        project_id="p1",
        deliverables=[],
    )
    assert decision.action == "silent"


def test_silent_in_scope():
    decision = route_classification(
        classification={"verdict": "IN_SCOPE", "confidence": 0.99},
        project_id="p1",
        deliverables=[],
    )
    assert decision.action == "silent"
