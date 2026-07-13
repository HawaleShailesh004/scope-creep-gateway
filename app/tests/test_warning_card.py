from listeners.views.warning_card import (
    build_change_order_stub_blocks,
    build_dismissed_blocks,
    build_warning_blocks,
)


def test_build_warning_blocks_includes_actions():
    blocks = build_warning_blocks(
        client_message="can you also add a blog section while you're at it?",
        new_task_summary="Add blog section",
        prior_mention_date=None,
        change_order_id="co-123",
        channel_id="C0BET8X49CZ",
        message_ts="1782998430.671389",
        project_id="53ce07f2-595f-4534-a5f2-c37739ef5712",
    )

    assert blocks[0]["type"] == "section"
    text = blocks[0]["text"]["text"]
    assert "Possible scope creep detected" in text
    assert "blog section" in text
    assert "Add blog section" in text

    actions = blocks[1]
    assert actions["type"] == "actions"
    action_ids = [el["action_id"] for el in actions["elements"]]
    assert action_ids == ["gen_change_order", "let_it_slide", "dismiss_creep"]
    draft_actions = blocks[2]
    assert draft_actions["elements"][0]["action_id"] == "draft_reply"


def test_build_warning_blocks_absorb_nudge():
    blocks = build_warning_blocks(
        client_message="add another page",
        new_task_summary="Extra page",
        prior_mention_date=None,
        change_order_id="co-789",
        channel_id="C0BET8X49CZ",
        message_ts="1782998430.671389",
        project_id="p1",
        absorb_nudge="_You've absorbed ₹3,500 from this client already - consider billing this one._",
    )
    assert "₹3,500" in blocks[0]["text"]["text"]


def test_build_absorbed_blocks():
    from listeners.views.warning_card import build_absorbed_blocks

    blocks = build_absorbed_blocks()
    assert "goodwill" in blocks[0]["text"]["text"].lower()


def test_build_warning_blocks_prior_mention_line():
    blocks = build_warning_blocks(
        client_message="add a blog",
        new_task_summary="Blog section",
        prior_mention_date="Jun 12, 2026",
        change_order_id="co-456",
        channel_id="C0BET8X49CZ",
        message_ts="1782998430.671389",
        project_id="p1",
    )

    text = blocks[0]["text"]["text"]
    assert "Jun 12, 2026" in text
    assert "also raised on" in text


def test_build_dismissed_blocks():
    blocks = build_dismissed_blocks()
    assert "Dismissed" in blocks[0]["text"]["text"]


def test_build_change_order_modal_has_submit():
    from listeners.views.change_order_modal import (
        build_change_order_modal,
        build_loading_change_order_modal,
    )

    loading = build_loading_change_order_modal(
        change_order_id="co-1",
        channel_id="C123",
        thread_ts="1.0",
        project_id="p1",
    )
    assert "Drafting" in loading["blocks"][0]["text"]["text"]
    assert "submit" not in loading

    modal = build_change_order_modal(
        change_order_id="co-1",
        channel_id="C123",
        thread_ts="1.0",
        project_id="p1",
        draft={
            "task_description": "Blog section",
            "estimated_cost": 3500,
            "timeline_impact_days": 4,
        },
    )
    assert modal["submit"]["text"] == "Post to channel"
