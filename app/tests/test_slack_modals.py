import pytest
from unittest.mock import AsyncMock, MagicMock

from services.slack_modals import open_view_with_trigger


@pytest.mark.asyncio
async def test_open_view_with_trigger_calls_views_open_before_ack():
    client = AsyncMock()
    client.views_open.return_value = {"view": {"id": "V1", "hash": "h1"}}
    ack = AsyncMock()
    order: list[str] = []

    async def track_open(**_kwargs):
        order.append("views_open")
        return {"view": {"id": "V1", "hash": "h1"}}

    async def track_ack():
        order.append("ack")

    client.views_open.side_effect = track_open
    ack.side_effect = track_ack

    result = await open_view_with_trigger(
        client,
        trigger_id="trigger",
        view={"type": "modal"},
        ack=ack,
    )

    assert result is not None
    assert order == ["views_open", "ack"]
    ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_open_view_with_trigger_handles_expired_trigger_id():
    from slack_sdk.errors import SlackApiError

    client = AsyncMock()
    ack = AsyncMock()
    response = MagicMock()
    response.get.return_value = "expired_trigger_id"
    client.views_open.side_effect = SlackApiError("expired", response)

    result = await open_view_with_trigger(
        client,
        trigger_id="trigger",
        view={"type": "modal"},
        ack=ack,
    )

    assert result is None
    ack.assert_awaited_once()
