import asyncio
import json
import logging

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.draft_reply_modal import POST_CALLBACK_ID, build_draft_reply_posted_modal
from services.freelancer_client import post_client_facing_message
from services.project_context import load_project_by_channel
from services.user_messages import (
    DRAFT_REPLY_EMPTY,
    DRAFT_REPLY_FREELANCER_ONLY,
    DRAFT_REPLY_POST_FAILED,
)

logger = logging.getLogger(__name__)

_POSTING_VIEW = {
    "type": "modal",
    "title": {"type": "plain_text", "text": "Posting…"},
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":hourglass_flowing_sand: Posting your reply to the channel…",
            },
        }
    ],
}


async def _views_update(
    client: AsyncWebClient,
    *,
    view_id: str,
    view: dict,
) -> None:
    try:
        await client.views_update(view_id=view_id, view=view)
    except SlackApiError as exc:
        if exc.response.get("error") == "hash_conflict":
            latest_hash = exc.response.get("view", {}).get("hash")
            await client.views_update(
                view_id=view_id,
                hash=latest_hash,
                view=view,
            )
            return
        raise


async def handle_draft_reply_post(
    ack,
    body: dict,
    client: AsyncWebClient,
    view: dict,
    logger: logging.Logger,
):
    metadata = json.loads(view.get("private_metadata", "{}"))
    channel_id = metadata["channel_id"]
    thread_ts = metadata.get("thread_ts") or None
    user_id = body["user"]["id"]
    view_id = body["view"]["id"]

    reply_text = (
        view.get("state", {})
        .get("values", {})
        .get("reply_block", {})
        .get("reply_text", {})
        .get("value", "")
        or ""
    ).strip()

    if not reply_text:
        await ack(
            response_action="errors",
            errors={"reply_block": DRAFT_REPLY_EMPTY},
        )
        return

    # Ack within 3s - post to channel after this, then views.update for result.
    await ack(response_action="update", view=_POSTING_VIEW)

    try:
        context = await asyncio.to_thread(load_project_by_channel, channel_id)
        if not context:
            await _views_update(
                client, view_id=view_id, view=_error_modal(DRAFT_REPLY_POST_FAILED)
            )
            return

        if user_id != context["project"].get("freelancer_slack_id"):
            await _views_update(
                client,
                view_id=view_id,
                view=_error_modal(DRAFT_REPLY_FREELANCER_ONLY),
            )
            return

        # Post as the freelancer so the client sees a human reply, not the bot.
        await post_client_facing_message(
            client,
            channel=channel_id,
            text=reply_text,
            thread_ts=thread_ts,
            team_id=body.get("team", {}).get("id"),
        )
        await _views_update(
            client, view_id=view_id, view=build_draft_reply_posted_modal()
        )
        logger.info(
            "draft_reply_posted channel_id=%s thread_ts=%s change_order_id=%s",
            channel_id,
            thread_ts,
            metadata.get("change_order_id"),
        )
    except SlackApiError as exc:
        logger.exception("draft_reply_post failed: %s", exc)
        try:
            await _views_update(
                client, view_id=view_id, view=_error_modal(DRAFT_REPLY_POST_FAILED)
            )
        except Exception:
            logger.exception("draft_reply_post error modal update failed")
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=DRAFT_REPLY_POST_FAILED,
        )


def _error_modal(message: str) -> dict:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Could not post"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
            }
        ],
    }


def register(app):
    app.view(POST_CALLBACK_ID)(handle_draft_reply_post)
