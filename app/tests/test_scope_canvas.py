from services.scope_canvas import (
    ANCHOR_CHANGE_LOG,
    ANCHOR_IN_SCOPE,
    ANCHOR_PENDING,
    ANCHOR_SCOPE_HEALTH,
    CanvasModel,
    ChangeLogEntry,
    Deliverable,
    build_full_canvas_markdown,
    section_markdown,
    status_section_markdown,
)


def test_full_canvas_has_core_sections():
    model = CanvasModel(
        project_name="Mnk Jewels",
        currency="INR",
        budget_total=50000,
        deadline="2026-07-15",
        health_committed=88,
        health_projected=76,
        budget_used_pct=16.0,
        timeline_used_pct=10.0,
        deliverables=[
            Deliverable("Homepage redesign", "setup"),
            Deliverable("Blog section", "change_order"),
        ],
        pending=[
            ChangeLogEntry("Jun 20", "FAQ page", 4000, 2, "proposed"),
        ],
        change_log=[
            ChangeLogEntry("Jun 20", "Blog section", 8000, 3, "paid"),
            ChangeLogEntry("Jul 01", "FAQ page", 4000, 2, "proposed"),
        ],
        freelancer_id="U123",
    )
    md = build_full_canvas_markdown(model)
    assert ANCHOR_SCOPE_HEALTH in md
    assert ANCHOR_IN_SCOPE in md
    assert "Added & agreed" in md
    assert ANCHOR_PENDING in md
    assert ANCHOR_CHANGE_LOG in md
    assert "Blog section" in md
    assert "88%" in md
    assert "projected 76%" in md
    assert "| FAQ page |" in md
    assert "<@U123>" in md


def test_status_section_includes_bars():
    model = CanvasModel(
        project_name="Acme",
        currency="INR",
        budget_total=50000,
        deadline=None,
        health_committed=100,
        health_projected=100,
        budget_used_pct=0,
        timeline_used_pct=0,
    )
    block = status_section_markdown(model)
    assert "Scope Health" in block
    assert "At a glance" in block


def test_section_markdown_by_anchor():
    model = CanvasModel(
        project_name="Acme",
        currency="INR",
        budget_total=50000,
        deadline=None,
        health_committed=100,
        health_projected=100,
        budget_used_pct=0,
        timeline_used_pct=0,
        deliverables=[Deliverable("Homepage", "setup")],
    )
    assert "Homepage" in section_markdown(model, ANCHOR_IN_SCOPE)
    assert "Nothing pending" in section_markdown(model, ANCHOR_PENDING)
