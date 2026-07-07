import pytest

from services.embedding_gate import (
    GateDecision,
    gate_message,
    stage1,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("thanks!", GateDecision.SKIP),
        ("Cheers mate", GateDecision.SKIP),
        ("Great work", GateDecision.SKIP),
        ("How is it going?", GateDecision.SKIP),
        ("Looks good 👍", GateDecision.SKIP),
        (":white_check_mark:", GateDecision.SKIP),
        ("", GateDecision.SKIP),
        ("Can you add a blog section?", GateDecision.ESCALATE),
        ("thanks, can you also add dark mode", GateDecision.ESCALATE),
        ("Is the checkout flow ready?", GateDecision.ESCALATE),
    ],
)
def test_stage1_confident_paths(text, expected):
    result = stage1(text)
    assert result is not None
    assert result.decision == expected


def test_stage1_unsure_falls_through():
    assert stage1("probably need something later") is None


def test_stage1_chatter_checkin_skips():
    result = stage1("Just checking in on progress")
    assert result is not None
    assert result.decision == GateDecision.SKIP


def test_gate_escalates_without_refs():
    result = gate_message("checking in on progress", refs=None)
    assert result.decision == GateDecision.ESCALATE
    assert result.stage == "fallback_escalate"


def test_gate_request_shaped_never_skips_even_with_empty_refs():
    result = gate_message("please update the footer copy", refs=None)
    assert result.decision == GateDecision.ESCALATE
    assert result.stage == "stage1_request"
