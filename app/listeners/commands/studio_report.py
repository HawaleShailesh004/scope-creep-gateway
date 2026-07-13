import asyncio
import json
import logging
import os

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from services.brief_template import format_budget
from services.studio_report import build_studio_weekly_summary
from services.user_messages import STUDIO_REPORT_LAUNCHER

logger = logging.getLogger(__name__)


def build_studio_report_launcher_blocks(*, channel_id: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": STUDIO_REPORT_LAUNCHER},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "action_id": "show_studio_report",
                    "text": {"type": "plain_text", "text": "View studio summary"},
                    "style": "primary",
                    "value": json.dumps({"ch": channel_id}),
                }
            ],
        },
    ]


async def handle_studio_report_command(
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
        text=STUDIO_REPORT_LAUNCHER,
        blocks=build_studio_report_launcher_blocks(channel_id=channel_id),
    )


async def handle_show_studio_report(
    ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    await ack()
    channel_id = json.loads(body["actions"][0]["value"])["ch"]
    user_id = body["user"]["id"]
    studio_name = (
        os.environ.get("STUDIO_NAME")
        or body.get("team", {}).get("domain")
        or "Keystone Digital Studio"
    )
    if studio_name == body.get("team", {}).get("domain"):
        studio_name = studio_name.replace("-", " ").title()

    summary = await asyncio.to_thread(
        build_studio_weekly_summary,
        user_id,
        studio_name=studio_name,
    )

    await client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=summary,
    )


def register(app: AsyncApp):
    app.command("/studio-report")(handle_studio_report_command)
