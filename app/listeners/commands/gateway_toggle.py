import asyncio
import logging

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from services.project_context import load_project_by_channel
from services.projects import set_classification_enabled
from services.user_messages import (
    GATEWAY_DISABLED,
    GATEWAY_ENABLED,
    GATEWAY_TOGGLE_FREELANCER_ONLY,
)

logger = logging.getLogger(__name__)


async def _toggle_gateway(
    *,
    body: dict,
    client: AsyncWebClient,
    enabled: bool,
    success_message: str,
):
    channel_id = body.get("channel_id")
    user_id = body["user_id"]
    if not channel_id:
        return

    context = await asyncio.to_thread(load_project_by_channel, channel_id)
    if not context:
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=GATEWAY_TOGGLE_FREELANCER_ONLY,
        )
        return

    project = context["project"]
    if user_id != project.get("freelancer_slack_id"):
        await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=GATEWAY_TOGGLE_FREELANCER_ONLY,
        )
        return

    await asyncio.to_thread(
        set_classification_enabled, project["id"], enabled
    )
    await client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=success_message,
    )


async def handle_gateway_off(
    ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    await ack()
    await _toggle_gateway(
        body=body,
        client=client,
        enabled=False,
        success_message=GATEWAY_DISABLED,
    )


async def handle_gateway_on(
    ack,
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    await ack()
    await _toggle_gateway(
        body=body,
        client=client,
        enabled=True,
        success_message=GATEWAY_ENABLED,
    )


def register(app: AsyncApp):
    app.command("/scope-gateway-off")(handle_gateway_off)
    app.command("/scope-gateway-on")(handle_gateway_on)
