"""CI safety tests for embedding gate - requires sentence-transformers."""
from __future__ import annotations

import pytest

from tests.fixtures.embedding_gate_corpus import PROJECTS, build_corpus
from services.embedding_gate import GateDecision, GateConfig, build_reference_vectors, gate_message


@pytest.fixture(scope="module")
def refs_cache():
    cache = {}
    for name, spec in PROJECTS.items():
        refs = build_reference_vectors(spec["deliverables"], spec["known_creep"])
        if not refs.ready:
            pytest.skip("sentence-transformers model unavailable")
        cache[name] = refs
    return cache


def test_corpus_zero_safety_violations(refs_cache):
    cfg = GateConfig()
    violations = []
    for entry in build_corpus():
        if not entry.safety_critical:
            continue
        refs = refs_cache[entry.project]
        result = gate_message(entry.text, refs, cfg)
        if result.decision == GateDecision.SKIP:
            violations.append((entry.category, entry.text, result.reason))
    assert not violations, f"critical requests skipped: {violations[:5]}"


def test_corpus_escalate_recall_on_requests(refs_cache):
    cfg = GateConfig()
    corpus = build_corpus()
    requests = [e for e in corpus if e.label == "escalate"]
    missed = []
    for entry in requests:
        refs = refs_cache[entry.project]
        result = gate_message(entry.text, refs, cfg)
        if result.decision != GateDecision.ESCALATE:
            missed.append(entry.text)
    assert not missed, f"requests not escalated: {missed[:5]}"


def test_skip_precision(refs_cache):
    """Every SKIP must be a labeled skip message - no false skips."""
    cfg = GateConfig()
    corpus = build_corpus()
    by_text = {e.text: e for e in corpus}
    false_skips = []
    for entry in corpus:
        refs = refs_cache[entry.project]
        result = gate_message(entry.text, refs, cfg)
        if result.decision == GateDecision.SKIP and entry.label != "skip":
            false_skips.append(entry.text)
    assert not false_skips, f"escalate-labeled messages skipped: {false_skips[:5]}"
