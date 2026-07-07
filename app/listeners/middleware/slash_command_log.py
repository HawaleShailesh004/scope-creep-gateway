import logging

from slack_bolt.async_app import AsyncApp

logger = logging.getLogger(__name__)


def register(app: AsyncApp) -> None:
    @app.middleware
    async def log_slash_commands(body, next):
        command = body.get("command")
        if command:
            logger.info(
                "slash_command_received command=%s user=%s channel=%s",
                command,
                body.get("user_id"),
                body.get("channel_id"),
            )
        return await next()
