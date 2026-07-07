import asyncio
import logging
import os

from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from listeners import register_listeners
from services.retention import purge_expired_text

load_dotenv(dotenv_path=".env", override=False)

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

RETENTION_INTERVAL_SECONDS = 6 * 60 * 60

app = AsyncApp(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    client=AsyncWebClient(
        base_url=os.environ.get("SLACK_API_URL", "https://slack.com/api"),
        token=os.environ.get("SLACK_BOT_TOKEN"),
    ),
)

register_listeners(app)


async def _retention_loop():
    while True:
        try:
            await asyncio.to_thread(purge_expired_text)
        except Exception:
            logger.exception("retention_purge_failed")
        await asyncio.sleep(RETENTION_INTERVAL_SECONDS)


async def main():
    try:
        await asyncio.to_thread(purge_expired_text)
    except Exception:
        logger.exception("retention_purge_startup_failed")

    asyncio.create_task(_retention_loop())
    handler = AsyncSocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())