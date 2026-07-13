import asyncio
import json
import logging

from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.change_order_card import (
    build_change_order_card_blocks,
    build_client_payment_ephemeral_blocks,
    build_freelancer_draft_ephemeral_blocks,
)
from listeners.views.change_order_modal import CALLBACK_ID
from services.canvas_sync import refresh_project_canvas
from services.change_orders import (
    change_order_number,
    get_change_order,
    update_change_order_proposed,
)
from services.ephemeral_updates import post_or_update_ephemeral
from services.freelancer_client import (
    post_client_facing_message,
    update_client_facing_message,
)
from services.operation_locks import LockKeys, operation_lock
from services.project_context import load_project_by_channel
from services.user_messages import (
    CANVAS_UPDATE_FAILED,
    CHANGE_ORDER_ALREADY_POSTED,
    CHANGE_ORDER_ALREADY_PROCESSING,
    CHANGE_ORDER_NO_LONGER_AVAILABLE,
    CHANGE_ORDER_POSTED_SUCCESS,
    CHANGE_ORDER_POSTING,
    POST_CHANGE_ORDER_FAILED,
)

logger = logging.getLogger(__name__)


def _parse_cost(raw: str | None) -> float:
    if not raw or not raw.strip():
        raise ValueError("Cost is required")
    try:
        from decimal import Decimal, InvalidOperation

        return float(Decimal(raw.strip().replace(",", "")))
    except InvalidOperation as exc:
        raise ValueError("Cost must be a number") from exc


def _parse_days(raw: str | None) -> int:
    if not raw or not raw.strip():
        raise ValueError("Timeline impact is required")
    try:
        days = int(raw.strip())
    except ValueError as exc:
        raise ValueError("Timeline impact must be a whole number") from exc
    if days < 0:
        raise ValueError("Timeline impact cannot be negative")
    return days


async def handle_change_order_submission(
    ack,
    body: dict,
    client: AsyncWebClient,
    view: dict,
    logger: logging.Logger,
):
    metadata = json.loads(view.get("private_metadata", "{}"))
    values = view.get("state", {}).get("values", {})
    user_id = body.get("user", {}).get("id")
    status_ts: str | None = None

    try:
        task_description = (
            values.get("task_block", {}).get("task_description", {}).get("value") or ""
        ).strip()
        estimated_cost = _parse_cost(
            values.get("cost_block", {}).get("estimated_cost", {}).get("value")
        )
        timeline_impact_days = _parse_days(
            values.get("days_block", {}).get("timeline_impact_days", {}).get("value")
        )

        if not task_description:
            await ack(
                response_action="errors",
                errors={"task_block": "Task description is required"},
            )
            return

        await ack()

        change_order_id = metadata["change_order_id"]
        channel_id = metadata["channel_id"]
        thread_ts = metadata.get("thread_ts") or None
        project_id = metadata["project_id"]

        async with operation_lock(LockKeys.change_order_submit(change_order_id)) as acquired:
            if not acquired:
                if user_id:
                    await client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text=CHANGE_ORDER_ALREADY_PROCESSING,
                    )
                return

            change_order = await asyncio.to_thread(get_change_order, change_order_id)
            if not change_order:
                raise RuntimeError("Change order not found")

            if change_order.get("status") in ("proposed", "paid"):
                if user_id:
                    await client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text=CHANGE_ORDER_ALREADY_POSTED,
                    )
                return

            if user_id:
                status_ts = await post_or_update_ephemeral(
                    client,
                    channel_id=channel_id,
                    user_id=user_id,
                    text=CHANGE_ORDER_POSTING,
                )

            context = await asyncio.to_thread(load_project_by_channel, channel_id)
            if not context:
                raise RuntimeError("Project not found for channel")

            project = context["project"]
            currency = project.get("currency") or "INR"

            updated = await asyncio.to_thread(
                update_change_order_proposed,
                change_order_id,
                task_description=task_description,
                estimated_cost=estimated_cost,
                timeline_impact_days=timeline_impact_days,
            )
            if not updated:
                if user_id:
                    await client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text=CHANGE_ORDER_NO_LONGER_AVAILABLE,
                    )
                return

            order_number = await asyncio.to_thread(
                change_order_number, project_id, change_order_id
            )
            title = (
                change_order.get("task_description")
                or task_description.split(".")[0][:40]
                or "Additional work"
            )

            team_id = body.get("team", {}).get("id")
            posted = await post_client_facing_message(
                client,
                channel=channel_id,
                text=f"Change Order #{order_number} - {title}",
                thread_ts=thread_ts,
                team_id=team_id,
            )
            message_ts = posted["ts"]

            blocks = build_change_order_card_blocks(
                order_number=order_number,
                title=title,
                task_description=task_description,
                estimated_cost=estimated_cost,
                timeline_impact_days=timeline_impact_days,
                budget_total=project.get("budget_total"),
                currency=currency,
                change_order_id=change_order_id,
                channel_id=channel_id,
                message_ts=message_ts,
                thread_ts=thread_ts or message_ts,
                project_id=project_id,
                include_payment=False,
                include_draft_reply=False,
            )
            await update_client_facing_message(
                client,
                channel=channel_id,
                ts=message_ts,
                text=f"Change Order #{order_number} - {title}",
                blocks=blocks,
                team_id=team_id,
            )

            client_slack_id = project.get("client_slack_id")
            if client_slack_id:
                await client.chat_postEphemeral(
                    channel=channel_id,
                    user=client_slack_id,
                    text=f"Change Order #{order_number} — payment options",
                    blocks=build_client_payment_ephemeral_blocks(
                        order_number=order_number,
                        title=title,
                        change_order_id=change_order_id,
                        channel_id=channel_id,
                        message_ts=message_ts,
                        thread_ts=thread_ts or message_ts,
                    ),
                )

            freelancer_id = project.get("freelancer_slack_id")
            if freelancer_id:
                await client.chat_postEphemeral(
                    channel=channel_id,
                    user=freelancer_id,
                    text=f"Change Order #{order_number} posted",
                    blocks=build_freelancer_draft_ephemeral_blocks(
                        order_number=order_number,
                        change_order_id=change_order_id,
                        channel_id=channel_id,
                        project_id=project_id,
                        thread_ts=thread_ts or message_ts,
                    ),
                )

            scope_health, canvas_updated = await refresh_project_canvas(
                channel_id, project_id
            )

            if user_id:
                if canvas_updated:
                    success_text = CHANGE_ORDER_POSTED_SUCCESS.format(
                        order_number=order_number,
                        scope_health=scope_health,
                    )
                else:
                    success_text = (
                        CHANGE_ORDER_POSTED_SUCCESS.format(
                            order_number=order_number,
                            scope_health=scope_health,
                        )
                        + "\n\n"
                        + CANVAS_UPDATE_FAILED.format(scope_health=scope_health)
                    )
                await post_or_update_ephemeral(
                    client,
                    channel_id=channel_id,
                    user_id=user_id,
                    text=success_text,
                    message_ts=status_ts,
                )

            logger.info(
                "change_order_posted %s",
                json.dumps(
                    {
                        "change_order_id": change_order_id,
                        "channel_id": channel_id,
                        "message_ts": message_ts,
                        "scope_health": scope_health,
                    },
                    ensure_ascii=False,
                ),
            )

    except ValueError as exc:
        await ack(
            response_action="errors",
            errors={"cost_block": str(exc)},
        )
    except Exception as exc:
        logger.exception("change order submission failed: %s", exc)
        if user_id:
            await post_or_update_ephemeral(
                client,
                channel_id=metadata.get("channel_id"),
                user_id=user_id,
                text=POST_CHANGE_ORDER_FAILED,
                message_ts=status_ts,
            )


def register(app):
    app.view(CALLBACK_ID)(handle_change_order_submission)
