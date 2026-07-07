import asyncio
import json
import logging

from slack_bolt import Ack
from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.change_order_card import build_change_order_card_blocks
from services.canvas_sync import refresh_project_canvas
from services.change_orders import (
    change_order_number,
    get_change_order,
    mark_change_order_paid,
)
from services.deliverables import ensure_deliverable_for_paid_order
from services.operation_locks import LockKeys, operation_lock
from services.project_context import load_project_by_channel
from services.user_messages import CHANGE_ORDER_CANNOT_PAY, SIMULATE_PAYMENT_FREELANCER_ONLY

logger = logging.getLogger(__name__)


def _parse_action_value(body: dict) -> dict:
    return json.loads(body["actions"][0]["value"])


async def _render_paid_card(
    client: AsyncWebClient,
    *,
    change_order: dict,
    change_order_id: str,
    channel_id: str,
    message_ts: str,
    thread_ts: str,
    project: dict,
    project_id: str,
) -> None:
    currency = project.get("currency") or "INR"
    order_number = await asyncio.to_thread(
        change_order_number, project_id, change_order_id
    )
    title = (
        change_order.get("task_description") or "Additional work"
    ).split(".")[0][:40]

    blocks = build_change_order_card_blocks(
        order_number=order_number,
        title=title,
        task_description=change_order.get("task_description") or "",
        estimated_cost=float(change_order.get("estimated_cost") or 0),
        timeline_impact_days=int(change_order.get("timeline_impact_days") or 0),
        budget_total=project.get("budget_total"),
        currency=currency,
        change_order_id=change_order_id,
        channel_id=channel_id,
        message_ts=message_ts,
        thread_ts=thread_ts,
        project_id=project_id,
        paid=True,
    )
    await client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text=f"Change Order #{order_number} - Paid",
        blocks=blocks,
    )
    await refresh_project_canvas(channel_id, project_id)


async def handle_simulate_payment(
    ack: Ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    await ack()

    try:
        payload = _parse_action_value(body)
        change_order_id = payload["co_id"]
        channel_id = payload["ch"]
        message_ts = payload["msg_ts"]
        thread_ts = payload.get("thread_ts", message_ts)
        user_id = body.get("user", {}).get("id")

        async with operation_lock(LockKeys.payment(change_order_id)) as acquired:
            if not acquired:
                if user_id:
                    await client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text=CHANGE_ORDER_CANNOT_PAY,
                    )
                return

            change_order = await asyncio.to_thread(get_change_order, change_order_id)
            if not change_order:
                return

            context = await asyncio.to_thread(load_project_by_channel, channel_id)
            if not context:
                return

            project = context["project"]
            project_id = project["id"]

            if user_id and user_id != project.get("freelancer_slack_id"):
                await client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=SIMULATE_PAYMENT_FREELANCER_ONLY,
                )
                return

            if change_order.get("status") == "paid":
                await asyncio.to_thread(
                    ensure_deliverable_for_paid_order, change_order
                )
                await _render_paid_card(
                    client,
                    change_order=change_order,
                    change_order_id=change_order_id,
                    channel_id=channel_id,
                    message_ts=message_ts,
                    thread_ts=thread_ts,
                    project=project,
                    project_id=project_id,
                )
                logger.info(
                    "change_order_paid_idempotent change_order_id=%s", change_order_id
                )
                return

            if change_order.get("status") != "proposed":
                if user_id:
                    await client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text=CHANGE_ORDER_CANNOT_PAY,
                    )
                return

            paid = await asyncio.to_thread(mark_change_order_paid, change_order_id)
            if not paid:
                refreshed = await asyncio.to_thread(get_change_order, change_order_id)
                if refreshed and refreshed.get("status") == "paid":
                    await asyncio.to_thread(
                        ensure_deliverable_for_paid_order, refreshed
                    )
                    await _render_paid_card(
                        client,
                        change_order=refreshed,
                        change_order_id=change_order_id,
                        channel_id=channel_id,
                        message_ts=message_ts,
                        thread_ts=thread_ts,
                        project=project,
                        project_id=project_id,
                    )
                return

            change_order = paid
            await asyncio.to_thread(ensure_deliverable_for_paid_order, change_order)
            await _render_paid_card(
                client,
                change_order=change_order,
                change_order_id=change_order_id,
                channel_id=channel_id,
                message_ts=message_ts,
                thread_ts=thread_ts,
                project=project,
                project_id=project_id,
            )

            logger.info("change_order_paid change_order_id=%s", change_order_id)
    except Exception as exc:
        logger.exception("Failed to simulate payment: %s", exc)
