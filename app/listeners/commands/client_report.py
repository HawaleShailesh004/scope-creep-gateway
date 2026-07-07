import asyncio
import json
import logging

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from services.brief_template import format_budget
from services.clients import client_stats, resolve_client
from services.project_context import load_project_by_channel
from services.user_messages import CLIENT_REPORT, CLIENT_REPORT_EMPTY, CLIENT_REPORT_LAUNCHER

logger = logging.getLogger(__name__)


def build_client_report_launcher_blocks(*, channel_id: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": CLIENT_REPORT_LAUNCHER},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "action_id": "show_client_report",
                    "text": {"type": "plain_text", "text": "View client report"},
                    "value": json.dumps({"ch": channel_id}),
                }
            ],
        },
    ]


async def handle_client_report_command(
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

    await client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=CLIENT_REPORT_LAUNCHER,
        blocks=build_client_report_launcher_blocks(channel_id=channel_id),
    )


async def handle_show_client_report(
    ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    await ack()

    channel_id = json.loads(body["actions"][0]["value"])["ch"]
    user_id = body["user"]["id"]

    context = await asyncio.to_thread(load_project_by_channel, channel_id)
    if not context:
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=CLIENT_REPORT_EMPTY,
        )
        return

    project = context["project"]
    client_id = await asyncio.to_thread(
        resolve_client,
        freelancer_slack_id=project["freelancer_slack_id"],
        client_slack_id=project["client_slack_id"],
    )
    stats = await asyncio.to_thread(client_stats, client_id)
    currency = project.get("currency") or "INR"

    await client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=CLIENT_REPORT.format(
            client=stats.get("client_label", "Client"),
            project_count=stats.get("project_count", 0),
            open_flags=stats.get("open_flags", 0),
            absorbed_count=stats.get("absorbed_count", 0),
            absorbed_value=format_budget(stats.get("absorbed_value"), currency),
            absorbed_hours=stats.get("absorbed_hours", 0),
            billed_count=stats.get("billed_count", 0),
            approved_value=format_budget(stats.get("approved_value"), currency),
            pending_value=format_budget(stats.get("pending_value"), currency),
            monthly_asks=stats.get("monthly_asks", 0),
        ),
    )


def register(app: AsyncApp):
    app.command("/client-report")(handle_client_report_command)
