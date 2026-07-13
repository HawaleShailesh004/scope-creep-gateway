from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from classifier import FLAG_THRESHOLD, should_flag
from services.revisions import (
    find_target_deliverable,
    log_revision,
    revision_limit_breached,
)

# Auto-absorb disabled for now - every out-of-scope ask surfaces the warning card
# so the freelancer chooses Let it slide vs bill. Re-enable trivial/small silent
# absorb once demo testing is stable.
AUTO_ABSORB_SIZES: frozenset[str] = frozenset()
WARN_SIZES = frozenset({"trivial", "small", "significant", "major"})


@dataclass
class RouteDecision:
    action: str  # warn | auto_absorb | revision_warn | silent
    classification: dict[str, Any]
    deliverable: dict | None = None
    revision_breach: bool = False


def route_classification(
    *,
    classification: dict[str, Any],
    project_id: str,
    deliverables: list[dict],
) -> RouteDecision:
    """Decide how to handle a classifier result."""
    if classification.get("is_revision_request"):
        target_name = classification.get("target_deliverable")
        deliverable = find_target_deliverable(project_id, target_name)
        if deliverable and revision_limit_breached(deliverable):
            return RouteDecision(
                action="revision_warn",
                classification=classification,
                deliverable=deliverable,
                revision_breach=True,
            )
        if deliverable:
            log_revision(
                deliverable_id=deliverable["id"],
                trigger_message_ts=None,
            )
        return RouteDecision(
            action="silent",
            classification=classification,
            deliverable=deliverable,
        )

    verdict = classification.get("verdict")
    confidence = float(classification.get("confidence", 0))
    size = (classification.get("size") or "significant").lower()

    if verdict == "OUT_OF_SCOPE":
        if size in AUTO_ABSORB_SIZES:
            return RouteDecision(
                action="auto_absorb",
                classification=classification,
            )
        if size in WARN_SIZES and confidence >= FLAG_THRESHOLD:
            return RouteDecision(
                action="warn",
                classification=classification,
            )
        if should_flag(classification):
            return RouteDecision(
                action="warn",
                classification=classification,
            )

    return RouteDecision(action="silent", classification=classification)
