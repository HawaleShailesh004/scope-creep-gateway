import asyncio
import json
import logging
from decimal import Decimal, InvalidOperation

from slack_bolt import Ack, Respond
from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.update_brief_modal import build_update_brief_modal
from services.brief_update import load_setup_deliverables
from services.project_context import load_project_by_channel
from services.slack_modals import notify_trigger_expired, open_view_with_trigger
from services.user_messages import (
    TRIGGER_EXPIRED_FORM_BUTTON,
    UPDATE_BRIEF_FREELANCER_ONLY,
    UPDATE_BRIEF_NO_PROJECT,
)

logger = logging.getLogger(__name__)


def _parse_action_value(body: dict) -> dict:
    return json.loads(body["actions"][0]["value"])


async def handle_open_update_brief(
    ack: Ack,
    body: dict,
    client: AsyncWebClient,
    respond: Respond,
    logger: logging.Logger,
):
    payload = _parse_action_value(body)
    channel_id = payload["channel_id"]
    user_id = body["user"]["id"]

    context = await asyncio.to_thread(load_project_by_channel, channel_id)
    if not context:
        await ack()
        await respond(replace_original=True, text=UPDATE_BRIEF_NO_PROJECT)
        return

    project = context["project"]
    if user_id != project.get("freelancer_slack_id"):
        await ack()
        await respond(replace_original=True, text=UPDATE_BRIEF_FREELANCER_ONLY)
        return

    setup_rows = await asyncio.to_thread(load_setup_deliverables, project["id"])
    deliverables = [row["description"] for row in setup_rows]
    revision_limit = None
    if setup_rows and setup_rows[0].get("revision_limit") is not None:
        revision_limit = str(setup_rows[0]["revision_limit"])

    budget = project.get("budget_total")
    budget_str = str(int(budget)) if budget is not None else None

    opened = await open_view_with_trigger(
        client,
        trigger_id=body["trigger_id"],
        view=build_update_brief_modal(
            channel_id=channel_id,
            project_id=project["id"],
            freelancer_id=user_id,
            project_name=project["project_name"],
            deliverables=deliverables or context["deliverables"][:1],
            budget=budget_str,
            deadline=project.get("deadline"),
            revision_limit=revision_limit,
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

    await respond(
        replace_original=True,
        text=":white_check_mark: The brief editor is open above — save when ready.",
    )
    logger.info("update_brief_modal_opened channel_id=%s", channel_id)
