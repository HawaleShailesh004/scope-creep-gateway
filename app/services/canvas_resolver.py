from __future__ import annotations

import json
import logging
import re

from slack_sdk.web.async_client import AsyncWebClient

from db.supabase_client import get_supabase
from services.slack_mcp import _mcp_request, is_valid_canvas_id

logger = logging.getLogger(__name__)

FILE_ID_RE = re.compile(r"File ID:\s*(F[A-Z0-9]{8,})")


def save_project_canvas_id(project_id: str, canvas_id: str) -> None:
    if not is_valid_canvas_id(canvas_id):
        raise ValueError(f"Refusing to save invalid canvas id: {canvas_id!r}")
    supabase = get_supabase()
    supabase.table("projects").update({"canvas_id": canvas_id}).eq(
        "id", project_id
    ).execute()


def brief_canvas_title(project_name: str) -> str:
    return f"Scope Health - {project_name}"


def _parse_canvas_ids_from_search(text: str) -> list[str]:
    return FILE_ID_RE.findall(text)


async def resolve_canvas_id_by_brief_title(
    user_token: str,
    project_name: str,
) -> str | None:
    title = brief_canvas_title(project_name)
    query = f'type:canvas "{title}"'
    result = await _mcp_request(
        user_token,
        "tools/call",
        {
            "name": "slack_search_public_and_private",
            "arguments": {
                "query": query,
                "limit": 5,
                "content_types": ["files"],
            },
        },
    )
    content = result.get("result", {}).get("content", [])
    if not isinstance(content, list) or not content:
        return None

    text = content[0].get("text", "")
    if not text:
        return None

    try:
        payload = json.loads(text)
        text = payload.get("results", text)
    except json.JSONDecodeError:
        pass

    for canvas_id in _parse_canvas_ids_from_search(text):
        if await _canvas_matches_project(user_token, canvas_id, project_name):
            return canvas_id
    return None


async def _canvas_matches_project(
    user_token: str,
    canvas_id: str,
    project_name: str,
) -> bool:
    try:
        result = await _mcp_request(
            user_token,
            "tools/call",
            {
                "name": "slack_read_canvas",
                "arguments": {"canvas_id": canvas_id},
            },
        )
        content = result.get("result", {}).get("content", [])
        if not content:
            return False
        payload = json.loads(content[0].get("text", "{}"))
        markdown = payload.get("markdown_content", "")
        return project_name in markdown and "Scope Health" in markdown
    except Exception as exc:
        logger.debug("Could not read canvas %s: %s", canvas_id, exc)
        return False


async def resolve_canvas_id_from_channel(
    user_token: str,
    channel_id: str,
) -> str | None:
    client = AsyncWebClient(token=user_token)
    response = await client.conversations_info(channel=channel_id)
    channel = response.get("channel", {})
    properties = channel.get("properties", {})
    tabs = list(properties.get("tabs", [])) + list(properties.get("tabz", []))
    for tab in tabs:
        if tab.get("type") != "canvas":
            continue
        file_id = tab.get("data", {}).get("file_id")
        if is_valid_canvas_id(file_id):
            return file_id
    return None


async def ensure_project_canvas_id(
    *,
    project_id: str,
    channel_id: str,
    stored_canvas_id: str | None,
    user_token: str,
    project_name: str,
) -> str | None:
    searched = await resolve_canvas_id_by_brief_title(user_token, project_name)
    if searched:
        if searched != stored_canvas_id:
            logger.info(
                "Resolved brief canvas %s for project %s (was %r)",
                searched,
                project_id,
                stored_canvas_id,
            )
            save_project_canvas_id(project_id, searched)
        return searched

    if is_valid_canvas_id(stored_canvas_id):
        if await _canvas_matches_project(user_token, stored_canvas_id, project_name):
            return stored_canvas_id
        # MCP read can flake; still prefer the stored id over failing the update.
        logger.warning(
            "Stored canvas %s for project %s failed content match; using it anyway",
            stored_canvas_id,
            project_id,
        )
        return stored_canvas_id

    resolved = await resolve_canvas_id_from_channel(user_token, channel_id)
    if not resolved:
        logger.warning(
            "No canvas found for project %s in channel %s (stored id=%r)",
            project_id,
            channel_id,
            stored_canvas_id,
        )
        return None

    if await _canvas_matches_project(user_token, resolved, project_name):
        if resolved != stored_canvas_id:
            logger.info(
                "Resolved channel-tab canvas %s for project %s (was %r)",
                resolved,
                project_id,
                stored_canvas_id,
            )
            save_project_canvas_id(project_id, resolved)
        return resolved

    logger.warning(
        "Channel tab canvas %s does not match project %r; skipping canvas update",
        resolved,
        project_name,
    )
    return None
