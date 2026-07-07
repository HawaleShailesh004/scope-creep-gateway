import json
import logging

from slack_bolt import Ack
from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.draft_reply_modal import build_draft_reply_modal
from services.slack_modals import notify_trigger_expired, open_view_with_trigger
from services.user_messages import TRIGGER_EXPIRED_FORM_BUTTON

logger = logging.getLogger(__name__)


def _parse_action_value(body: dict) -> dict:
    return json.loads(body["actions"][0]["value"])


def _thread_ts_from_payload(payload: dict) -> str | None:
    return (
        payload.get("ts")
        or payload.get("thread_ts")
        or payload.get("msg_ts")
        or None
    )


async def handle_draft_reply(
    ack: Ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    payload = _parse_action_value(body)
    change_order_id = payload["co_id"]
    channel_id = payload["ch"]
    project_id = payload["pid"]
    thread_ts = _thread_ts_from_payload(payload)
    user_id = body["user"]["id"]

    opened = await open_view_with_trigger(
        client,
        trigger_id=body["trigger_id"],
        view=build_draft_reply_modal(
            change_order_id=change_order_id,
            channel_id=channel_id,
            project_id=project_id,
            thread_ts=thread_ts,
        ),
        ack=ack,
    )
    if not opened:
        await notify_trigger_expired(
            client,
            channel_id=channel_id,
            user_id=user_id,
            text=TRIGGER_EXPIRED_FORM_BUTTON,
        )
        return

    logger.info("draft_reply_modal_opened change_order_id=%s", change_order_id)
