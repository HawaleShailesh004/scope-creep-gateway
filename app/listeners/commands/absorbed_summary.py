import asyncio
import logging

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from services.absorbed import format_absorbed_total, running_total
from services.project_context import load_project_by_channel
from services.user_messages import ABSORBED_SUMMARY, ABSORBED_SUMMARY_EMPTY

logger = logging.getLogger(__name__)


async def handle_absorbed_command(
    ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    await ack()

    channel_id = body.get("channel_id")
    user_id = body["user_id"]
    if not channel_id:
        return

    context = await asyncio.to_thread(load_project_by_channel, channel_id)
    if not context:
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=ABSORBED_SUMMARY_EMPTY,
        )
        return

    project = context["project"]
    totals = await asyncio.to_thread(running_total, project_id=project["id"])
    currency = project.get("currency") or "INR"

    if totals["count"] == 0:
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=ABSORBED_SUMMARY_EMPTY,
        )
        return

    await client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=ABSORBED_SUMMARY.format(
            manual_count=totals["manual_count"],
            auto_count=totals["auto_count"],
            total_value=format_absorbed_total(totals, currency),
        ),
    )


def register(app: AsyncApp):
    app.command("/absorbed")(handle_absorbed_command)
