from unittest.mock import AsyncMock, Mock

import pytest

from services.scope_warnings import send_scope_warning


@pytest.mark.asyncio
async def test_send_scope_warning_uses_channel_kwarg(monkeypatch):
    client = Mock()
    client.chat_postEphemeral = AsyncMock(return_value={"ok": True})

    monkeypatch.setattr(
        "services.scope_warnings.flag_already_exists", lambda *_a, **_k: False
    )
    monkeypatch.setattr(
        "services.scope_warnings._lookup_prior_mention",
        lambda **_k: (False, None),
    )
    monkeypatch.setattr(
        "services.scope_warnings.create_scope_flag",
        lambda **_k: "co-test",
    )
    monkeypatch.setattr(
        "services.scope_warnings._build_nudges",
        lambda **_k: (None, None, None),
    )
    monkeypatch.setattr(
        "services.scope_warnings.build_warning_blocks",
        lambda **_k: [{"type": "section", "text": {"type": "mrkdwn", "text": "x"}}],
    )

    await send_scope_warning(
        client,
        channel_id="C123",
        freelancer_id="U456",
        message_ts="1.0",
        message_text="add chat section",
        project={"id": "p1", "disclosure_ts": "0.5"},
        classification={"new_task_summary": "Chat section", "confidence": 0.9},
    )

    client.chat_postEphemeral.assert_awaited_once()
    kwargs = client.chat_postEphemeral.await_args.kwargs
    assert kwargs["channel"] == "C123"
    assert kwargs["user"] == "U456"
