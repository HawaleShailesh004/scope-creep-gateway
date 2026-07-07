import asyncio
import json
import logging
import os
from decimal import Decimal, InvalidOperation

from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from db.supabase_client import get_supabase
from listeners.views.setup_brief_launcher import build_setup_brief_launcher_blocks
from listeners.views.setup_brief_modal import CALLBACK_ID
from services.brief_template import build_canvas_markdown, parse_deliverables
from services.canvas_resolver import save_project_canvas_id
from services.clients import resolve_client
from services.deliverables import save_exclusions
from services.embedding_cache import refresh_embedding_refs
from services.operation_locks import LockKeys, is_locked, operation_lock
from services.projects import save_disclosure_ts
from services.slack_mcp import SlackMcpError, create_channel_canvas
from services.ephemeral_updates import post_or_update_ephemeral
from services.user_messages import (
    BRIEF_ALREADY_EXISTS,
    DISCLOSURE_NOTICE,
    SETUP_CLIENT_CANNOT_BE_FREELANCER,
    SETUP_CREATING,
    SETUP_FAILED,
    SETUP_FREELANCER_ONLY_HINT,
    SETUP_IN_PROGRESS,
    SETUP_LAUNCHER_INTRO,
    SETUP_SUCCESS_CHANNEL,
    SETUP_SUCCESS_EPHEMERAL,
    SETUP_SUCCESS_NOT_IN_CHANNEL,
)

logger = logging.getLogger(__name__)


def _parse_budget(raw: str | None) -> Decimal | None:
    if not raw or not raw.strip():
        return None
    try:
        return Decimal(raw.strip().replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("Budget must be a number") from exc


def _get_view_values(view: dict) -> dict:
    values = view.get("state", {}).get("values", {})
    return {
        "project_name": values["project_name_block"]["project_name"]["value"],
        "deliverables": values["deliverables_block"]["deliverables"]["value"],
        "budget": values.get("budget_block", {}).get("budget", {}).get("value"),
        "deadline": values.get("deadline_block", {}).get("deadline", {}).get(
            "selected_date"
        ),
        "client_user": values["client_user_block"]["client_user"]["selected_user"],
        "client_label": values.get("client_label_block", {})
        .get("client_label", {})
        .get("value"),
        "revision_limit": values.get("revision_limit_block", {})
        .get("revision_limit", {})
        .get("value"),
        "exclusions": values.get("exclusions_block", {})
        .get("exclusions", {})
        .get("value"),
    }


async def _notify_user(
    client: AsyncWebClient,
    *,
    channel_id: str | None,
    user_id: str,
    text: str,
    message_ts: str | None = None,
) -> str | None:
    return await post_or_update_ephemeral(
        client,
        channel_id=channel_id,
        user_id=user_id,
        text=text,
        message_ts=message_ts,
    )


async def _ensure_bot_in_channel(
    client: AsyncWebClient,
    channel_id: str,
    logger: logging.Logger,
) -> None:
    try:
        await client.conversations_join(channel=channel_id)
    except SlackApiError as exc:
        error = exc.response.get("error", "")
        if error not in ("already_in_channel", "method_not_supported_for_channel_type"):
            logger.warning("Could not join channel %s: %s", channel_id, error)


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


def _save_project_brief(
    *,
    channel_id: str,
    team_id: str,
    freelancer_id: str,
    client_slack_id: str,
    project_name: str,
    deliverables: list[str],
    budget_total: Decimal | None,
    deadline: str | None,
    client_label: str | None = None,
    default_revision_limit: int | None = None,
    exclusions: list[str] | None = None,
) -> str:
    supabase = get_supabase()
    project_row = {
        "slack_channel_id": channel_id,
        "slack_team_id": team_id,
        "freelancer_slack_id": freelancer_id,
        "client_slack_id": client_slack_id,
        "project_name": project_name,
        "budget_total": float(budget_total) if budget_total is not None else None,
        "currency": "INR",
        "deadline": deadline,
        "scope_health": 100,
    }
    project_result = supabase.table("projects").insert(project_row).execute()
    project_id = project_result.data[0]["id"]

    resolve_client(
        freelancer_slack_id=freelancer_id,
        client_slack_id=client_slack_id,
        client_label=client_label,
    )

    deliverable_rows = [
        {
            "project_id": project_id,
            "description": item,
            "origin": "setup",
            "revision_limit": default_revision_limit,
        }
        for item in deliverables
    ]
    supabase.table("deliverables").insert(deliverable_rows).execute()
    if exclusions:
        save_exclusions(project_id, exclusions)
    return project_id


async def handle_setup_brief_ack(ack):
    await ack()


async def handle_setup_brief_launcher(
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    channel_id = body.get("channel_id")
    user_id = body["user_id"]
    team_id = body.get("team_id") or (body.get("team") or {}).get("id")
    if not channel_id:
        logger.warning("setup-brief invoked outside a channel")
        return
    if not team_id:
        logger.warning("setup-brief missing team_id")
        return

    try:
        if await asyncio.to_thread(_channel_has_project, channel_id):
            await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=BRIEF_ALREADY_EXISTS,
            )
            return

        if is_locked(LockKeys.setup(channel_id)):
            await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=SETUP_IN_PROGRESS,
            )
            return

        # Post a launcher button so the button click provides a fresh trigger_id.
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"{SETUP_LAUNCHER_INTRO}\n\n_{SETUP_FREELANCER_ONLY_HINT}_",
            blocks=build_setup_brief_launcher_blocks(
                channel_id=channel_id,
                team_id=team_id,
            ),
        )
    except SlackApiError as exc:
        logger.exception(
            "setup-brief launcher ephemeral failed: %s",
            exc.response.get("error"),
        )
    except Exception:
        logger.exception("setup-brief launcher failed")


async def handle_setup_brief_submission(
    ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
    view: dict,
):
    metadata = json.loads(view.get("private_metadata", "{}"))
    channel_id = metadata.get("channel_id")
    team_id = metadata.get("team_id")
    freelancer_id = metadata.get("freelancer_id")
    user_id = body["user"]["id"]
    status_ts: str | None = None

    try:
        fields = _get_view_values(view)
        project_name = (fields["project_name"] or "").strip()
        deliverables = parse_deliverables(fields["deliverables"] or "")
        budget_total = _parse_budget(fields["budget"])
        deadline = fields["deadline"]
        client_slack_id = fields["client_user"]
        client_label = (fields.get("client_label") or "").strip() or None
        exclusions = parse_deliverables(fields.get("exclusions") or "")
        revision_raw = (fields.get("revision_limit") or "").strip()
        default_revision_limit = int(revision_raw) if revision_raw.isdigit() else None

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
        if not client_slack_id:
            await ack(
                response_action="errors",
                errors={"client_user_block": "Select the client"},
            )
            return
        if client_slack_id == freelancer_id:
            await ack(
                response_action="errors",
                errors={"client_user_block": SETUP_CLIENT_CANNOT_BE_FREELANCER},
            )
            return

        # Slack requires ack within ~3s - close the modal before Supabase/MCP work.
        await ack()

        if await asyncio.to_thread(_channel_has_project, channel_id):
            await _notify_user(
                client,
                channel_id=channel_id,
                user_id=user_id,
                text=BRIEF_ALREADY_EXISTS,
            )
            return

        async with operation_lock(LockKeys.setup(channel_id)) as acquired:
            if not acquired:
                await _notify_user(
                    client,
                    channel_id=channel_id,
                    user_id=user_id,
                    text=SETUP_IN_PROGRESS,
                )
                return

            status_ts = await _notify_user(
                client,
                channel_id=channel_id,
                user_id=user_id,
                text=SETUP_CREATING,
            )

            if await asyncio.to_thread(_channel_has_project, channel_id):
                await _notify_user(
                    client,
                    channel_id=channel_id,
                    user_id=user_id,
                    text=BRIEF_ALREADY_EXISTS,
                    message_ts=status_ts,
                )
                return

            project_id = await asyncio.to_thread(
                _save_project_brief,
                channel_id=channel_id,
                team_id=team_id,
                freelancer_id=freelancer_id,
                client_slack_id=client_slack_id,
                project_name=project_name,
                deliverables=deliverables,
                budget_total=budget_total,
                deadline=deadline,
                client_label=client_label,
                default_revision_limit=default_revision_limit,
                exclusions=exclusions,
            )

            canvas_markdown = build_canvas_markdown(
                project_name=project_name,
                deliverables=deliverables,
                budget_total=budget_total,
                deadline=deadline,
                freelancer_id=freelancer_id,
            )

            user_token = os.environ.get("SLACK_USER_TOKEN")
            if not user_token:
                raise RuntimeError(
                    "SLACK_USER_TOKEN is required for Canvas creation via MCP. "
                    "Copy the User OAuth Token from your app settings."
                )

            canvas_id = await create_channel_canvas(
                user_token,
                title=f"Project Brief - {project_name}",
                content=canvas_markdown,
                channel_id=channel_id,
            )

            await asyncio.to_thread(save_project_canvas_id, project_id, canvas_id)
            await asyncio.to_thread(refresh_embedding_refs, project_id, deliverables)

            await _ensure_bot_in_channel(client, channel_id, logger)

            disclosure_text = DISCLOSURE_NOTICE.format(
                freelancer=f"<@{freelancer_id}>"
            )

            try:
                await client.chat_postMessage(
                    channel=channel_id,
                    text=SETUP_SUCCESS_CHANNEL.format(project_name=project_name),
                )
                disclosure_msg = await client.chat_postMessage(
                    channel=channel_id,
                    text=disclosure_text,
                )
                if disclosure_msg.get("ts"):
                    await asyncio.to_thread(
                        save_disclosure_ts, project_id, disclosure_msg["ts"]
                    )
                await _notify_user(
                    client,
                    channel_id=channel_id,
                    user_id=user_id,
                    text=SETUP_SUCCESS_EPHEMERAL.format(project_name=project_name),
                    message_ts=status_ts,
                )
            except SlackApiError as exc:
                if exc.response.get("error") == "not_in_channel":
                    await _notify_user(
                        client,
                        channel_id=channel_id,
                        user_id=user_id,
                        text=SETUP_SUCCESS_NOT_IN_CHANNEL.format(
                            project_name=project_name
                        ),
                        message_ts=status_ts,
                    )
                else:
                    raise

    except ValueError as exc:
        await ack(
            response_action="errors",
            errors={"budget_block": str(exc)},
        )
    except (SlackMcpError, Exception) as exc:
        logger.exception("setup-brief submission failed")
        await _notify_user(
            client,
            channel_id=channel_id,
            user_id=user_id,
            text=SETUP_FAILED,
            message_ts=status_ts,
        )


def register(app: AsyncApp):
    app.command("/setup-brief")(
        ack=handle_setup_brief_ack,
        lazy=[handle_setup_brief_launcher],
    )
    app.view(CALLBACK_ID)(handle_setup_brief_submission)
