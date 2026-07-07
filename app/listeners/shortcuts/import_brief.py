import asyncio
import logging
import os

from slack_bolt import Ack
from slack_sdk.web.async_client import AsyncWebClient

from db.supabase_client import get_supabase
from services.import_brief_flow import extract_brief_from_message, open_prefilled_setup_modal
from services.operation_locks import LockKeys, is_locked
from services.slack_modals import notify_trigger_expired
from services.user_messages import (
    BRIEF_ALREADY_EXISTS,
    IMPORT_BRIEF_FAILED,
    IMPORT_BRIEF_NO_FILE,
    SETUP_IN_PROGRESS,
    TRIGGER_EXPIRED_FORM_BUTTON,
)

logger = logging.getLogger(__name__)


def _channel_has_project(channel_id: str) -> bool:
    supabase = get_supabase()
    existing = (
        supabase.table("projects")
        .select("id")
        .eq("slack_channel_id", channel_id)
        .limit(1)
        .execute()
    )
    return bool(existing.data)


async def handle_import_brief(
    ack: Ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    user_id = body["user"]["id"]
    channel_id = body.get("channel", {}).get("id")
    team_id = body.get("team", {}).get("id") or body.get("team_id")
    message = body.get("message", {})

    if not channel_id or not team_id:
        await ack()
        return

    if is_locked(LockKeys.setup(channel_id)):
        await ack()
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=SETUP_IN_PROGRESS,
        )
        return

    if await asyncio.to_thread(_channel_has_project, channel_id):
        await ack()
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=BRIEF_ALREADY_EXISTS,
        )
        return

    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not bot_token:
        await ack()
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=IMPORT_BRIEF_FAILED,
        )
        return

    extracted = await extract_brief_from_message(bot_token=bot_token, message=message)
    if not extracted:
        await ack()
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=IMPORT_BRIEF_NO_FILE,
        )
        return

    opened = await open_prefilled_setup_modal(
        client,
        trigger_id=body["trigger_id"],
        ack=ack,
        channel_id=channel_id,
        team_id=team_id,
        freelancer_id=user_id,
        extracted=extracted,
    )
    if not opened:
        await notify_trigger_expired(
            client,
            channel_id=channel_id,
            user_id=user_id,
            text=TRIGGER_EXPIRED_FORM_BUTTON,
        )
        return

    logger.info("import_brief_modal_opened channel_id=%s", channel_id)
