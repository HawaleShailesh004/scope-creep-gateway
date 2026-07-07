import asyncio
import json
import logging

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.draft_reply_modal import (
    CALLBACK_ID,
    build_draft_reply_result_modal,
)
from services.change_orders import get_change_order
from services.project_context import load_project_by_channel
from services.reply_drafter import draft_client_reply
from services.user_messages import DRAFT_REPLY_FAILED

logger = logging.getLogger(__name__)

_LOADING_VIEW = {
    "type": "modal",
    "title": {"type": "plain_text", "text": "Draft the reply"},
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":hourglass_flowing_sand: Drafting your message…",
            },
        }
    ],
}


async def _views_update(
    client: AsyncWebClient,
    *,
    view_id: str,
    view_hash: str | None,
    view: dict,
) -> str | None:
    """Update an open modal; omit hash to use Slack's latest view state."""
    kwargs: dict = {"view_id": view_id, "view": view}
    if view_hash:
        kwargs["hash"] = view_hash
    try:
        resp = await client.views_update(**kwargs)
        return resp["view"]["hash"]
    except SlackApiError as exc:
        error = exc.response.get("error")
        if error == "hash_conflict":
            latest_hash = exc.response.get("view", {}).get("hash")
            retry: dict = {"view_id": view_id, "view": view}
            if latest_hash:
                retry["hash"] = latest_hash
            resp = await client.views_update(**retry)
            return resp["view"]["hash"]
        raise


async def handle_draft_reply_submission(
    ack,
    body: dict,
    client: AsyncWebClient,
    view: dict,
    logger: logging.Logger,
):
    metadata = json.loads(view.get("private_metadata", "{}"))
    change_order_id = metadata["change_order_id"]
    channel_id = metadata["channel_id"]
    thread_ts = metadata.get("thread_ts") or None
    view_id = body["view"]["id"]
    user_id = body.get("user", {}).get("id")

    values = view.get("state", {}).get("values", {})
    tone = (
        values.get("tone_block", {})
        .get("tone", {})
        .get("selected_option", {})
        .get("value", "neutral")
    )

    # Must ack with update — plain ack() closes the modal and views.update → not_found.
    await ack(response_action="update", view=_LOADING_VIEW)

    error_view = {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Draft the reply"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": DRAFT_REPLY_FAILED},
            }
        ],
    }

    try:
        change_order = await asyncio.to_thread(get_change_order, change_order_id)
        if not change_order:
            raise RuntimeError("Change order not found")

        context = await asyncio.to_thread(load_project_by_channel, channel_id)
        if not context:
            raise RuntimeError("Project not found")

        project = context["project"]
        reply = await asyncio.to_thread(
            draft_client_reply,
            brief_markdown=context["brief_markdown"],
            deliverables=context["deliverables"],
            client_message=change_order.get("trigger_text") or "",
            task_summary=change_order.get("task_description"),
            estimated_cost=change_order.get("estimated_cost")
            or change_order.get("estimated_value"),
            timeline_impact_days=change_order.get("timeline_impact_days"),
            currency=project.get("currency") or "INR",
            tone=tone,
        )

        await _views_update(
            client,
            view_id=view_id,
            view_hash=None,
            view=build_draft_reply_result_modal(
                reply_text=reply,
                tone=tone,
                channel_id=channel_id,
                thread_ts=thread_ts,
                change_order_id=change_order_id,
            ),
        )
        logger.info("draft_reply_generated change_order_id=%s tone=%s", change_order_id, tone)
    except Exception as exc:
        logger.exception("draft_reply failed: %s", exc)
        try:
            await _views_update(
                client,
                view_id=view_id,
                view_hash=None,
                view=error_view,
            )
        except SlackApiError as update_exc:
            if update_exc.response.get("error") != "not_found":
                logger.exception("draft_reply error modal update failed")
        except Exception:
            logger.exception("draft_reply error modal update failed")
        if user_id and channel_id:
            await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=DRAFT_REPLY_FAILED,
            )


def register(app):
    app.view(CALLBACK_ID)(handle_draft_reply_submission)
