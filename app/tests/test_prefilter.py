from services.prefilter import is_project_channel_message, should_skip_message


def test_should_skip_bot_and_short_messages():
    assert should_skip_message({"bot_id": "B123", "text": "hello there friend"})
    assert should_skip_message({"subtype": "message_changed", "text": "hello there friend"})
    assert should_skip_message({"text": "ok thanks"})
    assert not should_skip_message({"text": "can you add a blog section"})


def test_is_project_channel_message():
    assert is_project_channel_message({"channel_type": "channel"})
    assert is_project_channel_message({"channel_type": "group"})
    assert is_project_channel_message({"channel": "C0BET8X49CZ"})
    assert is_project_channel_message({"channel": "G01234567"})
    assert not is_project_channel_message({"channel_type": "im"})
    assert not is_project_channel_message({"channel": "D01234567"})
