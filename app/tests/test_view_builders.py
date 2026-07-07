from listeners.views.app_home_builder import build_app_home_view
from listeners.views.feedback_builder import build_feedback_blocks


def test_build_feedback_blocks():
    blocks = build_feedback_blocks()

    assert len(blocks) > 0
    block_dict = blocks[0].to_dict()
    action_ids = [e["action_id"] for e in block_dict["elements"]]
    assert "feedback" in action_ids


def test_build_app_home_view_default():
    view = build_app_home_view()

    assert view["type"] == "home"
    header = view["blocks"][0]["text"]["text"]
    assert "Scope Creep Gateway" in header

    body = view["blocks"][1]["text"]["text"]
    assert "/setup-brief" in body
    assert "/change-order" in body


def test_build_app_home_view_connect():
    view = build_app_home_view(install_url="https://example.com/slack/install")

    context_text = view["blocks"][-1]["elements"][0]["text"]
    assert "MCP" in context_text
    assert "https://example.com/slack/install" in context_text


def test_build_app_home_view_connected():
    view = build_app_home_view(is_connected=True)

    context_text = view["blocks"][-1]["elements"][0]["text"]
    assert "connected" in context_text
