import asyncio

import logging

import os

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from services.projects import load_project_by_channel
from services.user_messages import BOT_JOIN_INTRO

logger = logging.getLogger(__name__)


async def handle_member_joined_channel(
    event: dict,
    client: AsyncWebClient,
    context,
    logger: logging.Logger,
):
    """Post a short intro when the bot joins a channel (no disclosure here)."""
    bot_user_id = context.get("bot_user_id") or os.environ.get("SLACK_BOT_USER_ID")
    if not bot_user_id:
        auth = await client.auth_test()
        bot_user_id = auth.get("user_id")

    if event.get("user") != bot_user_id:
        return

    channel_id = event.get("channel")
    if not channel_id:
        return

    project = await asyncio.to_thread(load_project_by_channel, channel_id)
    if project:
        # Full disclosure is posted once on successful /setup-brief.
        return

    try:
        await client.chat_postMessage(channel=channel_id, text=BOT_JOIN_INTRO)
    except Exception as exc:
        logger.warning("member_joined intro post failed: %s", exc)


def register(app: AsyncApp):
    app.event("member_joined_channel")(handle_member_joined_channel)
