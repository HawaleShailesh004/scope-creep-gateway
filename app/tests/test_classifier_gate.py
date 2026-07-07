from classifier import should_flag


def test_should_flag_only_high_confidence_out_of_scope():
    assert should_flag({"verdict": "OUT_OF_SCOPE", "confidence": 0.85})
    assert not should_flag({"verdict": "OUT_OF_SCOPE", "confidence": 0.7})
    assert not should_flag({"verdict": "AMBIGUOUS", "confidence": 0.95})
    assert not should_flag({"verdict": "IN_SCOPE", "confidence": 0.99})
