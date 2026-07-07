import logging

from slack_bolt import Ack
from slack_sdk.web.async_client import AsyncWebClient

from services.change_order_flow import open_change_order_bootstrap_modal
from services.operation_locks import LockKeys, is_locked
from services.slack_modals import notify_trigger_expired
from services.user_messages import (
    CHANGE_ORDER_FLAG_IN_PROGRESS,
    TRIGGER_EXPIRED_SCOPE_FLAG,
)

logger = logging.getLogger(__name__)


async def handle_flag_scope_change(
    ack: Ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    user_id = body["user"]["id"]
    channel_id = body.get("channel", {}).get("id")
    message = body.get("message", {})
    message_ts = message.get("ts")
    message_text = (message.get("text") or "").strip()

    if not channel_id or not message_ts:
        await ack()
        return

    if is_locked(LockKeys.bootstrap(channel_id, user_id)):
        await ack()
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=CHANGE_ORDER_FLAG_IN_PROGRESS,
        )
        return

    opened = await open_change_order_bootstrap_modal(
        client,
        trigger_id=body["trigger_id"],
        ack=ack,
        channel_id=channel_id,
        user_id=user_id,
        thread_ts=message_ts,
        message_ts=message_ts,
        message_text=message_text,
        source="shortcut",
    )
    if not opened:
        await notify_trigger_expired(
            client,
            channel_id=channel_id,
            user_id=user_id,
            text=TRIGGER_EXPIRED_SCOPE_FLAG,
        )
        return

    logger.info("manual_scope_flag shortcut opened message_ts=%s", message_ts)
