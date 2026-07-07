import logging

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.change_order_launcher import build_change_order_launcher_blocks
from services.operation_locks import LockKeys, is_locked
from services.user_messages import CHANGE_ORDER_IN_PROGRESS, CHANGE_ORDER_LAUNCHER_INTRO

logger = logging.getLogger(__name__)


async def handle_change_order_command(
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

    if is_locked(LockKeys.bootstrap(channel_id, user_id)):
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=CHANGE_ORDER_IN_PROGRESS,
        )
        return

    await client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=CHANGE_ORDER_LAUNCHER_INTRO,
        blocks=build_change_order_launcher_blocks(channel_id=channel_id),
    )

    logger.info("change_order_launcher_posted channel_id=%s", channel_id)


def register(app: AsyncApp):
    app.command("/change-order")(handle_change_order_command)
