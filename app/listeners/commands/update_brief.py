import asyncio
import json
import logging
from decimal import Decimal, InvalidOperation

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.update_brief_launcher import build_update_brief_launcher_blocks
from services.project_context import load_project_by_channel
from services.user_messages import UPDATE_BRIEF_LAUNCHER_INTRO, UPDATE_BRIEF_NO_PROJECT

logger = logging.getLogger(__name__)


async def handle_update_brief_command(
    ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    await ack()

    channel_id = body.get("channel_id")
    user_id = body["user_id"]
    if not channel_id:
        return

    context = await asyncio.to_thread(load_project_by_channel, channel_id)
    if not context:
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=UPDATE_BRIEF_NO_PROJECT,
        )
        return

    await client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=UPDATE_BRIEF_LAUNCHER_INTRO,
        blocks=build_update_brief_launcher_blocks(channel_id=channel_id),
    )


def register(app: AsyncApp):
    app.command("/update-brief")(handle_update_brief_command)
