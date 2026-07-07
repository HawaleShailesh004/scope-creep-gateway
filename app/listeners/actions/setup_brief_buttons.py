import asyncio
import logging

from slack_bolt import Ack, Respond
from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.setup_brief_launcher import build_manual_brief_modal
from services.operation_locks import LockKeys, is_locked
from services.project_context import load_project_by_channel
from services.slack_modals import notify_trigger_expired, open_view_with_trigger
from services.user_messages import (
    BRIEF_ALREADY_EXISTS,
    SETUP_FORM_READY,
    SETUP_IN_PROGRESS,
    TRIGGER_EXPIRED_FORM_BUTTON,
)

logger = logging.getLogger(__name__)


def _parse_action_value(body: dict) -> dict:
    import json

    return json.loads(body["actions"][0]["value"])


async def handle_open_setup_brief(
    ack: Ack,
    body: dict,
    client: AsyncWebClient,
    respond: Respond,
    logger: logging.Logger,
):
    payload = _parse_action_value(body)
    channel_id = payload["channel_id"]
    team_id = payload["team_id"]
    user_id = body["user"]["id"]

    if is_locked(LockKeys.setup(channel_id)):
        await ack()
        await respond(replace_original=True, text=SETUP_IN_PROGRESS)
        return

    if await asyncio.to_thread(load_project_by_channel, channel_id):
        await ack()
        await respond(replace_original=True, text=BRIEF_ALREADY_EXISTS)
        return

    open_resp = await open_view_with_trigger(
        client,
        trigger_id=body["trigger_id"],
        view=build_manual_brief_modal(
            channel_id=channel_id,
            team_id=team_id,
            freelancer_id=user_id,
            empty_channel=False,
        ),
        ack=ack,
    )
    if not open_resp:
        await notify_trigger_expired(
            client,
            channel_id=channel_id,
            user_id=user_id,
            text=TRIGGER_EXPIRED_FORM_BUTTON,
        )
        return

    await respond(
        replace_original=True,
        text=SETUP_FORM_READY,
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": SETUP_FORM_READY},
            }
        ],
    )
    logger.info("setup_brief_modal_opened channel_id=%s", channel_id)
