import asyncio
import logging
import os

from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from listeners import register_listeners
from mode import RAILWAY_SLACK_EVENTS_URL, apply_mode, mode_banner, resolve_app_mode
from services.retention import purge_expired_text

load_dotenv(dotenv_path=".env", override=False)

# Resolve once at import so transport / OAuth behavior is consistent.
APP_MODE = resolve_app_mode()
apply_mode(APP_MODE)

RETENTION_INTERVAL_SECONDS = 6 * 60 * 60


def _configure_logging() -> logging.Logger:
    level_name = os.environ.get("LOG_LEVEL", "").strip().upper()
    if not level_name:
        # Default INFO - local DEBUG floods the asyncio loop (hpack) and can
        # delay Socket Mode acks enough to trigger Slack operation_timeout.
        level_name = "INFO"
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level)
    # These emit one INFO/DEBUG line per outbound request/model file, which floods
    # Railway's 500 logs/sec cap and can stall the asyncio loop locally.
    for noisy in (
        "httpx",
        "httpcore",
        "hpack",
        "huggingface_hub",
        "sentence_transformers",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger(__name__)


logger = _configure_logging()


def _transport() -> str:
    return APP_MODE.transport


def _build_app() -> AsyncApp:
    transport = _transport()
    # Single-workspace mode uses SLACK_BOT_TOKEN. If SLACK_CLIENT_ID/SECRET are
    # present (for app_oauth.py), Bolt auto-enables a file InstallationStore and
    # ignores the bot token - that can delay slash-command acks into
    # operation_timeout. Temporarily hide OAuth env vars for this App only.
    saved_oauth = {
        key: os.environ.pop(key)
        for key in ("SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET")
        if key in os.environ
    }
    try:
        kwargs: dict = {
            "client": AsyncWebClient(
                base_url=os.environ.get("SLACK_API_URL", "https://slack.com/api"),
                token=os.environ.get("SLACK_BOT_TOKEN"),
            ),
        }
        if transport == "http":
            signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "").strip()
            if not signing_secret:
                raise RuntimeError(
                    "SLACK_SIGNING_SECRET is required when APP_MODE=prod (HTTP)"
                )
            kwargs["signing_secret"] = signing_secret
            # Slash commands and interactivity must ack in the HTTP response body.
            kwargs["process_before_response"] = True
        app = AsyncApp(**kwargs)
        register_listeners(app)
        return app
    finally:
        os.environ.update(saved_oauth)


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


async def _warmup_embedding_gate():
    """Load MiniLM at boot so the first client message is not blocked on HF download."""
    try:
        from services.embedding_gate import _Embedder

        await asyncio.to_thread(_Embedder.get)
        logger.info("embedding_gate_warmup done")
    except Exception:
        logger.exception("embedding_gate_warmup_failed")


async def _start_socket_mode():
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

    app_token = os.environ.get("SLACK_APP_TOKEN", "").strip()
    if not app_token:
        raise RuntimeError("SLACK_APP_TOKEN is required when APP_MODE=dev (Socket Mode)")
    asyncio.create_task(_purge_on_startup())
    asyncio.create_task(_retention_loop())
    asyncio.create_task(_warmup_embedding_gate())
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
        # Slack retries an event (only the Events API sets this header) when it
        # doesn't get a 200 within 3s. Our message handler runs synchronously
        # (process_before_response), so a slow cold start triggers retries that
        # would double-process and create duplicate change orders. Ack retries
        # immediately without re-dispatching. Slash commands/interactivity do not
        # use this header, so they are unaffected.
        retry_num = request.headers.get("X-Slack-Retry-Num")
        if retry_num:
            logger.info(
                "slack_retry_ignored num=%s reason=%s",
                retry_num,
                request.headers.get("X-Slack-Retry-Reason"),
            )
            return web.Response(status=200, text="")

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
        "ScopeGuard listening on 0.0.0.0:%s (HTTP) path=%s "
        "process_before_response=%s expected_slack_url=%s",
        port,
        slack_path,
        app.process_before_response,
        RAILWAY_SLACK_EVENTS_URL,
    )
    asyncio.create_task(_purge_on_startup())
    asyncio.create_task(_retention_loop())
    asyncio.create_task(_warmup_embedding_gate())
    await asyncio.Event().wait()


async def main():
    print(mode_banner(APP_MODE), flush=True)
    logger.info("starting APP_MODE=%s transport=%s", APP_MODE.name, APP_MODE.transport)
    if APP_MODE.transport == "http":
        await _start_http()
    elif APP_MODE.transport == "socket":
        await _start_socket_mode()
    else:
        raise RuntimeError(f"Unknown transport={APP_MODE.transport!r}")


if __name__ == "__main__":
    asyncio.run(main())
