import asyncio
import logging

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from db.supabase_client import get_supabase
from listeners.views.import_brief_launcher import build_import_brief_launcher_blocks
from services.operation_locks import LockKeys, is_locked
from services.user_messages import BRIEF_ALREADY_EXISTS, IMPORT_BRIEF_LAUNCHER_INTRO, SETUP_IN_PROGRESS

logger = logging.getLogger(__name__)


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


async def handle_import_brief_ack(ack):
    await ack()


async def handle_import_brief_launcher(
    body: dict,
    client: AsyncWebClient,
    logger: logging.Logger,
):
    channel_id = body.get("channel_id")
    user_id = body["user_id"]
    team_id = body.get("team_id")
    if not channel_id or not team_id:
        logger.warning("import-brief invoked outside a channel")
        return

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

    await client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=IMPORT_BRIEF_LAUNCHER_INTRO,
        blocks=build_import_brief_launcher_blocks(
            channel_id=channel_id,
            team_id=team_id,
        ),
    )


def register(app: AsyncApp):
    app.command("/import-brief")(
        ack=handle_import_brief_ack,
        lazy=[handle_import_brief_launcher],
    )
