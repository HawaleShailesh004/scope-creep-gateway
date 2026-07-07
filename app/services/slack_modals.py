from __future__ import annotations

import logging
from typing import Any

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from services.user_messages import TRIGGER_EXPIRED

logger = logging.getLogger(__name__)

TRIGGER_EXPIRED_USER_MESSAGE = TRIGGER_EXPIRED


async def open_view_with_trigger(
    client: AsyncWebClient,
    *,
    trigger_id: str,
    view: dict,
    ack,
) -> dict[str, Any] | None:
    """
    Open a modal using a trigger_id, then ack the Slack request.

    Slack trigger_ids expire in ~3 seconds. Production apps always call
    views.open before ack() and before any network I/O (DB, AI API, etc.).
    """
    try:
        response = await client.views_open(trigger_id=trigger_id, view=view)
    except SlackApiError as exc:
        error = exc.response.get("error", "")
        if error == "expired_trigger_id":
            logger.warning(
                "expired_trigger_id - event was likely queued during a socket "
                "reconnect or the handler was too slow"
            )
            if ack is not None:
                await ack()
            return None
        raise

    if ack is not None:
        await ack()
    return response


async def notify_trigger_expired(
    client: AsyncWebClient,
    *,
    channel_id: str | None,
    user_id: str,
    text: str = TRIGGER_EXPIRED_USER_MESSAGE,
) -> None:
    if channel_id:
        await client.chat_postEphemeral(channel=channel_id, user=user_id, text=text)
    else:
        await client.chat_postMessage(channel=user_id, text=text)
