from datetime import date
from decimal import Decimal

from services.brief_template import (
    build_canvas_markdown,
    format_budget,
    parse_deliverables,
)


def test_parse_deliverables_strips_blank_lines():
    raw = "Homepage\n\nAbout page\n  \nContact form\n"
    assert parse_deliverables(raw) == ["Homepage", "About page", "Contact form"]


def test_format_budget_inr():
    assert format_budget(Decimal("50000")) == "₹50,000"


def test_build_canvas_markdown_includes_health_and_items():
    markdown = build_canvas_markdown(
        project_name="Acme redesign",
        deliverables=["Homepage", "About page"],
        budget_total=50000,
        deadline=date(2026, 7, 15),
    )
    assert "Acme redesign" in markdown
    assert "Scope Health:** 🟢 100%" in markdown
    assert "## In scope" in markdown
    assert "- Homepage" in markdown
    assert "- About page" in markdown
    assert "At a glance" in markdown


def test_build_canvas_markdown_with_change_log():
    markdown = build_canvas_markdown(
        project_name="Acme redesign",
        deliverables=["Homepage"],
        budget_total=50000,
        deadline=date(2026, 7, 15),
        scope_health=88,
        change_log_entries=["- Jun 20 - Blog section (+₹8,000, +3 days) - proposed"],
    )
    assert "Scope Health:** 🟢 88%" in markdown
    assert "Change log" in markdown
