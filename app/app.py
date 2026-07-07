import asyncio
import logging
import os

from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from listeners import register_listeners
from services.retention import purge_expired_text

load_dotenv(dotenv_path=".env", override=False)

RETENTION_INTERVAL_SECONDS = 6 * 60 * 60
RAILWAY_SLACK_EVENTS_URL = (
    "https://scope-creep-gateway-production.up.railway.app/slack/events"
)


def _configure_logging() -> logging.Logger:
    level_name = os.environ.get("LOG_LEVEL", "").strip().upper()
    if not level_name:
        # Railway sets PORT; default to INFO there to avoid log rate limits.
        level_name = "INFO" if os.environ.get("PORT") else "DEBUG"
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level)
    return logging.getLogger(__name__)


logger = _configure_logging()


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
        # Slash commands and interactivity must ack in the HTTP response body.
        kwargs["process_before_response"] = True
    app = AsyncApp(**kwargs)
    register_listeners(app)
    return app


app = _build_app()


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
    asyncio.create_task(_purge_on_startup())
    asyncio.create_task(_retention_loop())
    handler = AsyncSocketModeHandler(app, app_token)
    await handler.start_async()


async def _start_http():
    from aiohttp import web
    from slack_bolt.adapter.aiohttp import to_aiohttp_response, to_bolt_request

    port = int(os.environ.get("PORT", "3000"))
    slack_path = os.environ.get("SLACK_EVENTS_PATH", "/slack/events")

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    async def slack_events(request: web.Request) -> web.Response:
        bolt_req = await to_bolt_request(request)
        bolt_resp = await app.async_dispatch(bolt_req)
        if bolt_resp is None:
            logger.warning("slack_dispatch_returned_none path=%s", slack_path)
            return web.Response(status=200, text="")
        return await to_aiohttp_response(bolt_resp)

    http_app = web.Application()
    http_app.add_routes(
        [
            web.get("/health", health),
            web.post(slack_path, slack_events),
        ]
    )
    runner = web.AppRunner(http_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(
        "Scope Creep Gateway listening on 0.0.0.0:%s (HTTP) path=%s "
        "process_before_response=%s expected_slack_url=%s",
        port,
        slack_path,
        app.process_before_response,
        RAILWAY_SLACK_EVENTS_URL,
    )
    asyncio.create_task(_purge_on_startup())
    asyncio.create_task(_retention_loop())
    await asyncio.Event().wait()


async def main():
    transport = _transport()
    logger.info("starting transport=%s", transport)
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
