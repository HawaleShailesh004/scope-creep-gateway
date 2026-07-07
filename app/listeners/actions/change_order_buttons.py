import json
import logging

from slack_bolt import Ack, Respond
from slack_sdk.web.async_client import AsyncWebClient

from services.change_order_flow import open_change_order_bootstrap_modal
from services.operation_locks import LockKeys, is_locked
from services.slack_modals import notify_trigger_expired
from services.user_messages import (
    CHANGE_ORDER_FORM_READY,
    CHANGE_ORDER_IN_PROGRESS,
    CHANGE_ORDER_OPENING_FORM,
    TRIGGER_EXPIRED_FORM_BUTTON,
)

logger = logging.getLogger(__name__)


def _parse_action_value(body: dict) -> dict:
    return json.loads(body["actions"][0]["value"])


async def handle_open_change_order(
    ack: Ack,
    body: dict,
    client: AsyncWebClient,
    respond: Respond,
    logger: logging.Logger,
):
    payload = _parse_action_value(body)
    channel_id = payload["channel_id"]
    user_id = body["user"]["id"]

    if is_locked(LockKeys.bootstrap(channel_id, user_id)):
        await ack()
        await respond(replace_original=True, text=CHANGE_ORDER_IN_PROGRESS)
        return

    opened = await open_change_order_bootstrap_modal(
        client,
        trigger_id=body["trigger_id"],
        ack=ack,
        channel_id=channel_id,
        user_id=user_id,
        source="slash",
    )
    if not opened:
        if is_locked(LockKeys.bootstrap(channel_id, user_id)):
            await respond(replace_original=True, text=CHANGE_ORDER_IN_PROGRESS)
        else:
            await notify_trigger_expired(
                client,
                channel_id=channel_id,
                user_id=user_id,
                text=TRIGGER_EXPIRED_FORM_BUTTON,
            )
        return

    await respond(
        replace_original=True,
        text=CHANGE_ORDER_FORM_READY,
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": CHANGE_ORDER_FORM_READY},
            }
        ],
    )
    logger.info("change_order_modal_opened channel_id=%s", channel_id)
