from __future__ import annotations

import logging

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

logger = logging.getLogger(__name__)


async def post_or_update_ephemeral(
    client: AsyncWebClient,
    *,
    channel_id: str | None,
    user_id: str,
    text: str,
    message_ts: str | None = None,
) -> str | None:
    """
    Post a new ephemeral status or update an existing one in place.

    Returns message_ts when Slack provides it (for follow-up updates).
    """
    if channel_id and message_ts:
        try:
            await client.chat_update(channel=channel_id, ts=message_ts, text=text)
            return message_ts
        except SlackApiError as exc:
            logger.warning(
                "Could not update ephemeral ts=%s: %s",
                message_ts,
                exc.response.get("error"),
            )

    if channel_id:
        try:
            response = await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=text,
            )
            return response.get("message_ts")
        except SlackApiError:
            logger.exception("Failed to post ephemeral to channel %s", channel_id)

    try:
        await client.chat_postMessage(channel=user_id, text=text)
    except SlackApiError:
        logger.exception("Failed to DM status to user %s", user_id)
    return None
