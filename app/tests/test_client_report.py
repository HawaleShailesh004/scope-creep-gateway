from listeners.commands.client_report import build_client_report_launcher_blocks


def test_client_report_launcher_has_button():
    blocks = build_client_report_launcher_blocks(channel_id="C123")
    assert blocks[1]["elements"][0]["action_id"] == "show_client_report"
