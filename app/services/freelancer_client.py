"""Client for posting client-facing messages as the freelancer (not the bot).

Priority for the user token:
  1. SLACK_USER_TOKEN env (single-workspace / hackathon)
  2. OAuth FileInstallationStore user_token (distributed install via app_oauth.py)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from slack_sdk.web.async_client import AsyncWebClient

logger = logging.getLogger(__name__)

_INSTALL_DIR = Path(__file__).resolve().parent.parent / "data" / "installations"


def get_freelancer_user_token(*, team_id: str | None = None) -> str | None:
    env_token = (os.environ.get("SLACK_USER_TOKEN") or "").strip()
    if env_token:
        return env_token

    if team_id:
        from_store = _user_token_from_installation_store(team_id)
        if from_store:
            return from_store

    # Last resort: any cached installation (single-workspace demos)
    from_store = _user_token_from_installation_store(None)
    if from_store:
        return from_store

    return None


def _user_token_from_installation_store(team_id: str | None) -> str | None:
    try:
        from slack_sdk.oauth.installation_store import FileInstallationStore

        store = FileInstallationStore(base_dir=str(_INSTALL_DIR))
        if team_id:
            installation = store.find_installation(
                enterprise_id=None, team_id=team_id, is_enterprise_install=False
            )
            if installation and installation.user_token:
                return installation.user_token
            return None

        # No team filter - pick first installation with a user token (dev only).
        if not _INSTALL_DIR.exists():
            return None
        for path in _INSTALL_DIR.rglob("*.json"):
            try:
                import json

                data = json.loads(path.read_text(encoding="utf-8"))
                token = data.get("user_token") or data.get("userToken")
                if token:
                    return token
            except Exception:
                continue
    except Exception:
        logger.debug("installation_store_user_token_lookup_failed", exc_info=True)
    return None


def freelancer_client(*, team_id: str | None = None) -> AsyncWebClient | None:
    token = get_freelancer_user_token(team_id=team_id)
    if not token:
        logger.warning(
            "No freelancer user token - client-facing posts will use the bot. "
            "Set SLACK_USER_TOKEN or complete OAuth install (user scopes)."
        )
        return None
    return AsyncWebClient(
        base_url=os.environ.get("SLACK_API_URL", "https://slack.com/api"),
        token=token,
    )


async def post_client_facing_message(
    bot_client: AsyncWebClient,
    *,
    channel: str,
    text: str,
    thread_ts: str | None = None,
    blocks: list | None = None,
    team_id: str | None = None,
) -> dict:
    """Post as the freelancer when possible; otherwise fall back to the bot."""
    client = freelancer_client(team_id=team_id) or bot_client
    kwargs: dict = {"channel": channel, "text": text}
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
    if blocks is not None:
        kwargs["blocks"] = blocks
    return await client.chat_postMessage(**kwargs)


async def update_client_facing_message(
    bot_client: AsyncWebClient,
    *,
    channel: str,
    ts: str,
    text: str,
    blocks: list | None = None,
    team_id: str | None = None,
) -> dict:
    client = freelancer_client(team_id=team_id) or bot_client
    kwargs: dict = {"channel": channel, "ts": ts, "text": text}
    if blocks is not None:
        kwargs["blocks"] = blocks
    return await client.chat_update(**kwargs)
