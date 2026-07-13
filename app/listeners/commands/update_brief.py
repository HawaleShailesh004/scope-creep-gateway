import asyncio
import logging

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.update_brief_launcher import build_update_brief_launcher_blocks
from services.projects import load_project_by_channel
from services.user_messages import UPDATE_BRIEF_LAUNCHER_INTRO, UPDATE_BRIEF_NO_PROJECT

logger = logging.getLogger(__name__)


async def _send_update_brief_launcher(
    client: AsyncWebClient, *, channel_id: str, user_id: str
) -> None:
    try:
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
    except Exception:
        logger.exception("update_brief_launcher_failed channel=%s", channel_id)


async def handle_update_brief_command(
    ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    # Ack first and return immediately. With process_before_response (HTTP) Slack
    # only gets the ack when this listener returns; any DB work here causes
    # operation_timeout even though the ephemeral may still appear later.
    await ack()

    channel_id = body.get("channel_id")
    user_id = body.get("user_id")
    if not channel_id or not user_id:
        return

    asyncio.create_task(
        _send_update_brief_launcher(client, channel_id=channel_id, user_id=user_id)
    )


def register(app: AsyncApp):
    app.command("/update-brief")(handle_update_brief_command)
