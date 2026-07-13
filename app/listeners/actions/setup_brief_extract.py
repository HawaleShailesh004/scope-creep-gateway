import asyncio
import json
import logging
import os

from slack_bolt import Ack, Respond
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.setup_brief_launcher import build_manual_brief_modal
from services.operation_locks import LockKeys, is_locked
from services.project_context import load_project_by_channel
from services.scope_extractor import extract_brief_from_channel, fetch_channel_conversation
from services.slack_modals import notify_trigger_expired, open_view_with_trigger
from services.user_messages import (
    BRIEF_ALREADY_EXISTS,
    EXTRACT_FAILED,
    EXTRACT_IN_PROGRESS,
    SETUP_FORM_READY,
    SETUP_IN_PROGRESS,
    TRIGGER_EXPIRED_FORM_BUTTON,
)

logger = logging.getLogger(__name__)


def _parse_action_value(body: dict) -> dict:
    return json.loads(body["actions"][0]["value"])


async def _open_brief_modal(
    client: AsyncWebClient,
    *,
    trigger_id: str,
    channel_id: str,
    team_id: str,
    freelancer_id: str,
    ack: Ack | None,
    extracted: dict | None = None,
    empty_channel: bool = False,
    status_note: str | None = None,
) -> dict | None:
    view = build_manual_brief_modal(
        channel_id=channel_id,
        team_id=team_id,
        freelancer_id=freelancer_id,
        extracted=extracted,
        status_note=status_note,
        empty_channel=empty_channel,
    )
    try:
        if ack is not None:
            result = await open_view_with_trigger(
                client, trigger_id=trigger_id, view=view, ack=ack
            )
            return result.get("view") if result else None
        response = await client.views_open(trigger_id=trigger_id, view=view)
        return response.get("view")
    except SlackApiError as exc:
        if exc.response.get("error") == "expired_trigger_id":
            logger.warning("expired_trigger_id opening brief modal channel=%s", channel_id)
            return None
        raise


async def _update_brief_modal(
    client: AsyncWebClient,
    *,
    view_id: str,
    view_hash: str,
    channel_id: str,
    team_id: str,
    freelancer_id: str,
    extracted: dict | None,
) -> bool:
    view = build_manual_brief_modal(
        channel_id=channel_id,
        team_id=team_id,
        freelancer_id=freelancer_id,
        extracted=extracted,
    )
    try:
        await client.views_update(view_id=view_id, hash=view_hash, view=view)
        return True
    except SlackApiError as exc:
        logger.warning(
            "views_update failed channel=%s error=%s",
            channel_id,
            exc.response.get("error"),
        )
        return False


async def handle_extract_setup_brief(
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

    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not bot_token:
        await ack()
        await respond(replace_original=True, text=EXTRACT_FAILED)
        return

    messages = await fetch_channel_conversation(bot_token, channel_id, limit=20)

    # Always open the form immediately while trigger_id is valid.
    opened_view = await _open_brief_modal(
        client,
        trigger_id=body["trigger_id"],
        channel_id=channel_id,
        team_id=team_id,
        freelancer_id=user_id,
        ack=ack,
        extracted=None,
        empty_channel=not messages,
    )
    if not opened_view:
        await notify_trigger_expired(
            client,
            channel_id=channel_id,
            user_id=user_id,
            text=TRIGGER_EXPIRED_FORM_BUTTON,
        )
        return

    await respond(
        replace_original=True,
        text=SETUP_FORM_READY if not messages else EXTRACT_IN_PROGRESS,
    )

    if not messages:
        logger.info("setup_brief_empty_channel_opened channel_id=%s", channel_id)
        return

    view_id = opened_view["id"]
    view_hash = opened_view["hash"]

    try:
        extracted = await extract_brief_from_channel(bot_token, channel_id)
        updated = await _update_brief_modal(
            client,
            view_id=view_id,
            view_hash=view_hash,
            channel_id=channel_id,
            team_id=team_id,
            freelancer_id=user_id,
            extracted=extracted,
        )
        if updated:
            logger.info("setup_brief_extract_updated channel_id=%s", channel_id)
        else:
            await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=EXTRACT_FAILED,
            )
    except Exception as exc:
        logger.exception("extract_setup_brief_failed: %s", exc)
        await _update_brief_modal(
            client,
            view_id=view_id,
            view_hash=view_hash,
            channel_id=channel_id,
            team_id=team_id,
            freelancer_id=user_id,
            extracted=None,
        )
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=EXTRACT_FAILED,
        )


async def handle_open_extracted_brief(
    ack: Ack,
    body: dict,
    client: AsyncWebClient,
    respond: Respond,
    logger: logging.Logger,
):
    """Legacy fallback - opens manual form (draft cache path)."""
    payload = _parse_action_value(body)
    channel_id = payload["channel_id"]
    team_id = payload["team_id"]
    user_id = body["user"]["id"]

    await ack()

    if is_locked(LockKeys.setup(channel_id)) or await asyncio.to_thread(
        load_project_by_channel, channel_id
    ):
        return

    opened = await _open_brief_modal(
        client,
        trigger_id=body["trigger_id"],
        channel_id=channel_id,
        team_id=team_id,
        freelancer_id=user_id,
        ack=None,
    )
    if not opened:
        await notify_trigger_expired(
            client,
            channel_id=channel_id,
            user_id=user_id,
            text=TRIGGER_EXPIRED_FORM_BUTTON,
        )
        return

    await respond(replace_original=True, text=SETUP_FORM_READY)
