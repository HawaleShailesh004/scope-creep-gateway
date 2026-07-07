import json

from listeners.views.draft_reply_modal import (
    build_draft_reply_modal,
    build_draft_reply_result_modal,
)
from listeners.views.update_brief_modal import build_update_brief_modal


def test_draft_reply_modal_has_tone_options():
    modal = build_draft_reply_modal(
        change_order_id="co-1",
        channel_id="C1",
        project_id="p1",
        thread_ts="123.456",
    )
    options = modal["blocks"][1]["element"]["options"]
    values = [o["value"] for o in options]
    assert values == ["warm", "neutral", "firm"]
    assert json.loads(modal["private_metadata"])["thread_ts"] == "123.456"


def test_draft_reply_result_modal_has_editable_reply_and_post():
    modal = build_draft_reply_result_modal(
        reply_text="Thanks for the idea — let's scope this separately.",
        tone="neutral",
        channel_id="C1",
        thread_ts="123.456",
        change_order_id="co-1",
    )
    assert modal["callback_id"] == "draft_reply_post_submit"
    assert modal["submit"]["text"] == "Post to channel"
    reply_input = modal["blocks"][1]["element"]
    assert reply_input["type"] == "plain_text_input"
    assert reply_input["multiline"] is True
    assert "scope this separately" in reply_input["initial_value"]


def test_update_brief_modal_prefills_deliverables():
    modal = build_update_brief_modal(
        channel_id="C1",
        project_id="p1",
        freelancer_id="U1",
        project_name="Acme",
        deliverables=["Homepage", "About page"],
        budget="50000",
        deadline="2026-07-04",
        revision_limit="2",
    )
    deliverable_value = modal["blocks"][2]["element"]["initial_value"]
    assert "Homepage" in deliverable_value
    assert modal["submit"]["text"] == "Save changes"
