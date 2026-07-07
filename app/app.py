import asyncio
import logging
import os

from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from listeners import register_listeners
from services.retention import purge_expired_text

load_dotenv(dotenv_path=".env", override=False)

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

RETENTION_INTERVAL_SECONDS = 6 * 60 * 60


def _transport() -> str:
    explicit = os.environ.get("SLACK_TRANSPORT", "").strip().lower()
    if explicit:
        return explicit
    # Railway and most PaaS set PORT; use HTTP automatically in that case.
    if os.environ.get("PORT"):
        return "http"
    return "socket"


def _build_app() -> AsyncApp:
    transport = _transport()
    kwargs: dict = {
        "token": os.environ.get("SLACK_BOT_TOKEN"),
        "client": AsyncWebClient(
            base_url=os.environ.get("SLACK_API_URL", "https://slack.com/api"),
            token=os.environ.get("SLACK_BOT_TOKEN"),
        ),
    }
    if transport == "http":
        signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "").strip()
        if not signing_secret:
            raise RuntimeError(
                "SLACK_SIGNING_SECRET is required when SLACK_TRANSPORT=http"
            )
        kwargs["signing_secret"] = signing_secret
    return AsyncApp(**kwargs)


app = _build_app()
register_listeners(app)


async def _retention_loop():
    while True:
        try:
            await asyncio.to_thread(purge_expired_text)
        except Exception:
            logger.exception("retention_purge_failed")
        await asyncio.sleep(RETENTION_INTERVAL_SECONDS)


async def _purge_on_startup():
    try:
        await asyncio.to_thread(purge_expired_text)
    except Exception:
        logger.exception("retention_purge_startup_failed")


async def _start_socket_mode():
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

    app_token = os.environ.get("SLACK_APP_TOKEN", "").strip()
    if not app_token:
        raise RuntimeError("SLACK_APP_TOKEN is required when SLACK_TRANSPORT=socket")
    await _purge_on_startup()
    asyncio.create_task(_retention_loop())
    handler = AsyncSocketModeHandler(app, app_token)
    await handler.start_async()


async def _start_http():
    from aiohttp import web
    from slack_bolt.adapter.aiohttp.async_handler import AsyncSlackRequestHandler

    port = int(os.environ.get("PORT", "3000"))
    handler = AsyncSlackRequestHandler(app)

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    async def on_startup(_app: web.Application):
        await _purge_on_startup()
        asyncio.create_task(_retention_loop())
        logger.info("Scope Creep Gateway listening on 0.0.0.0:%s (HTTP)", port)

    http_app = web.Application()
    http_app.on_startup.append(on_startup)
    http_app.add_routes(
        [
            web.get("/health", health),
            web.post("/slack/events", handler.handle),
        ]
    )
    runner = web.AppRunner(http_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    await asyncio.Event().wait()


async def main():
    transport = _transport()
    if transport == "http":
        await _start_http()
    elif transport == "socket":
        await _start_socket_mode()
    else:
        raise RuntimeError(
            f"Unknown SLACK_TRANSPORT={transport!r} (use 'socket' or 'http')"
        )


if __name__ == "__main__":
    asyncio.run(main())
