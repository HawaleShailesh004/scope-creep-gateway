import asyncio
import json
import logging
from decimal import Decimal, InvalidOperation

from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.update_brief_modal import CALLBACK_ID
from services.brief_template import parse_deliverables
from services.brief_update import update_project_brief
from services.canvas_sync import refresh_project_canvas
from services.ephemeral_updates import post_or_update_ephemeral
from services.user_messages import (
    UPDATE_BRIEF_FAILED,
    UPDATE_BRIEF_SAVING,
    UPDATE_BRIEF_SUCCESS,
)

logger = logging.getLogger(__name__)


def _parse_budget(raw: str | None) -> Decimal | None:
    if not raw or not raw.strip():
        return None
    try:
        return Decimal(raw.strip().replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("Budget must be a number") from exc


async def handle_update_brief_submission(
    ack,
    body: dict,
    client: AsyncWebClient,
    view: dict,
    logger: logging.Logger,
):
    metadata = json.loads(view.get("private_metadata", "{}"))
    channel_id = metadata["channel_id"]
    project_id = metadata["project_id"]
    user_id = body.get("user", {}).get("id")
    status_ts: str | None = None

    values = view.get("state", {}).get("values", {})
    project_name = (
        values.get("project_name_block", {}).get("project_name", {}).get("value") or ""
    ).strip()
    deliverables_raw = (
        values.get("deliverables_block", {}).get("deliverables", {}).get("value") or ""
    )
    budget_raw = values.get("budget_block", {}).get("budget", {}).get("value")
    deadline = values.get("deadline_block", {}).get("deadline", {}).get("selected_date")
    revision_raw = (
        values.get("revision_limit_block", {}).get("revision_limit", {}).get("value")
        or ""
    ).strip()

    deliverables = parse_deliverables(deliverables_raw)

    if not project_name:
        await ack(
            response_action="errors",
            errors={"project_name_block": "Project name is required"},
        )
        return
    if not deliverables:
        await ack(
            response_action="errors",
            errors={"deliverables_block": "Add at least one deliverable"},
        )
        return

    try:
        budget_total = _parse_budget(budget_raw)
        default_revision_limit = int(revision_raw) if revision_raw.isdigit() else None
    except ValueError as exc:
        await ack(response_action="errors", errors={"budget_block": str(exc)})
        return

    await ack()

    try:
        if user_id:
            status_ts = await post_or_update_ephemeral(
                client,
                channel_id=channel_id,
                user_id=user_id,
                text=UPDATE_BRIEF_SAVING,
            )

        await asyncio.to_thread(
            update_project_brief,
            project_id=project_id,
            project_name=project_name,
            deliverables=deliverables,
            budget_total=budget_total,
            deadline=deadline,
            default_revision_limit=default_revision_limit,
        )
        await refresh_project_canvas(channel_id, project_id, mode="full")

        if user_id:
            await post_or_update_ephemeral(
                client,
                channel_id=channel_id,
                user_id=user_id,
                text=UPDATE_BRIEF_SUCCESS,
                message_ts=status_ts,
            )
        logger.info("update_brief_saved project_id=%s", project_id)
    except Exception as exc:
        logger.exception("update_brief failed: %s", exc)
        if user_id:
            await post_or_update_ephemeral(
                client,
                channel_id=channel_id,
                user_id=user_id,
                text=UPDATE_BRIEF_FAILED,
                message_ts=status_ts,
            )


def register(app):
    app.view(CALLBACK_ID)(handle_update_brief_submission)
