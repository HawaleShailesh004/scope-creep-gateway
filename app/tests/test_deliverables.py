from services.deliverables import (
    deliverable_descriptions,
    message_covered_by_deliverables,
)


def test_deliverable_descriptions_extracts_text(monkeypatch):
    from services import deliverables

    monkeypatch.setattr(
        deliverables,
        "load_effective_deliverables",
        lambda project_id: [
            {"description": "Homepage"},
            {"description": "Blog section", "origin": "change_order"},
        ],
    )
    assert deliverable_descriptions("p1") == ["Homepage", "Blog section"]


def test_message_covered_when_all_deliverable_tokens_in_message():
    deliverables = [
        "Homepage Redesign",
        "Redesign the blog section to align with the updated homepage",
    ]
    assert message_covered_by_deliverables(
        "can you align the blog section with the updated homepage pls?",
        deliverables,
    )


def test_message_not_covered_by_partial_token_overlap():
    """Shared words (blog) alone must not suppress classification."""
    deliverables = [
        "Admin dashboard for uploading and managing clothing listings",
    ]
    assert not message_covered_by_deliverables(
        "pls add new page for clothing listings", deliverables
    )


def test_message_not_covered_by_unrelated_deliverable():
    deliverables = [
        "Homepage Redesign",
        "Redesign the blog section to align with the updated homepage",
    ]
    assert not message_covered_by_deliverables(
        "can you also redesign the chat section pls", deliverables
    )


def test_message_covered_when_deliverable_token_subset():
    assert message_covered_by_deliverables(
        "tweak the homepage hero",
        ["Homepage Redesign"],
    )
