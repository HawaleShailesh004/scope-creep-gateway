from listeners.views.app_home_builder import build_app_home_view
from services.user_messages import APP_HOME_PRIVACY


def test_app_home_includes_privacy_block():
    view = build_app_home_view()
    texts = [b["text"]["text"] for b in view["blocks"] if b.get("type") == "section"]
    combined = "\n".join(texts)
    assert "Privacy" in combined or "privacy" in combined.lower()
    assert APP_HOME_PRIVACY.split("\n")[0] in combined
