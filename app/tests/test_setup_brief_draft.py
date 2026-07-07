from services.setup_brief_draft_cache import assess_extracted_brief


def test_assess_insufficient():
    result = assess_extracted_brief({"project_name": "", "deliverables": []})
    assert result["tier"] == "insufficient"


def test_assess_partial_name_only():
    result = assess_extracted_brief(
        {"project_name": "Acme redesign", "deliverables": []}
    )
    assert result["tier"] == "partial"
    assert "deliverables" in result["missing"]


def test_assess_good():
    result = assess_extracted_brief(
        {
            "project_name": "Acme redesign",
            "deliverables": ["Homepage"],
        }
    )
    assert result["tier"] == "good"
    assert "client" in result["missing"]
