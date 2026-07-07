from __future__ import annotations

import json
import logging
import re
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

SLACK_MCP_URL = "https://mcp.slack.com/mcp"
CANVAS_CREATE_TOOL_NAMES = (
    "create_a_canvas",
    "canvas_create",
    "slack_create_canvas",
)
CANVAS_UPDATE_TOOL_NAMES = (
    "update_a_canvas",
    "canvas_update",
    "slack_update_canvas",
    "edit_canvas",
)
DRAFT_TOOL_NAMES = (
    "slack_send_message_draft",
    "send_message_draft",
)

CANVAS_ID_RE = re.compile(r"^F[A-Z0-9]{8,}$")


class SlackMcpError(RuntimeError):
    pass


def is_valid_canvas_id(canvas_id: str | None) -> bool:
    return bool(canvas_id and CANVAS_ID_RE.match(canvas_id))


async def _mcp_request(
    user_token: str,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
    }
    if params is not None:
        payload["params"] = params

    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(SLACK_MCP_URL, json=payload, headers=headers) as resp:
            body = await resp.text()
            if resp.status >= 400:
                raise SlackMcpError(f"MCP HTTP {resp.status}: {body[:500]}")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SlackMcpError(f"MCP returned non-JSON response: {body[:500]}") from exc

    if "error" in data:
        raise SlackMcpError(f"MCP error: {data['error']}")

    return data


async def _discover_canvas_tool(
    user_token: str, candidates: tuple[str, ...], *, keyword: str
) -> str:
    result = await _mcp_request(user_token, "tools/list")
    tools = result.get("result", {}).get("tools", [])
    names = {tool.get("name", "") for tool in tools}
    for candidate in candidates:
        if candidate in names:
            return candidate
    for name in names:
        if keyword in name.lower() and "canvas" in name.lower():
            return name
    raise SlackMcpError(
        f"No canvas {keyword} tool found. Available tools: {sorted(names)}"
    )


def _canvas_id_from_value(value: Any) -> str | None:
    if not value:
        return None
    candidate = str(value).strip()
    return candidate if is_valid_canvas_id(candidate) else None


def _extract_canvas_id(result: dict[str, Any]) -> str:
    tool_result = result.get("result", {})

    structured = tool_result.get("structuredContent")
    if isinstance(structured, dict):
        for key in ("canvas_id", "id", "file_id"):
            canvas_id = _canvas_id_from_value(structured.get(key))
            if canvas_id:
                return canvas_id

    content = tool_result.get("content", [])
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            text = block.get("text", "")
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                for key in ("canvas_id", "id", "file_id"):
                    canvas_id = _canvas_id_from_value(payload.get(key))
                    if canvas_id:
                        return canvas_id
            match = re.search(r"F[A-Z0-9]{8,}", text)
            if match and is_valid_canvas_id(match.group(0)):
                return match.group(0)

    raise SlackMcpError(f"Could not parse canvas id from MCP response: {result}")


async def create_channel_canvas(
    user_token: str,
    *,
    title: str,
    content: str,
    channel_id: str,
) -> str:
    tool_name = await _discover_canvas_tool(
        user_token, CANVAS_CREATE_TOOL_NAMES, keyword="create"
    )
    arguments: dict[str, Any] = {
        "title": title,
        "content": content,
        "channel_id": channel_id,
    }

    logger.info("Calling MCP tool %s for channel %s", tool_name, channel_id)
    result = await _mcp_request(
        user_token,
        "tools/call",
        {"name": tool_name, "arguments": arguments},
    )
    return _extract_canvas_id(result)


async def update_channel_canvas(
    user_token: str,
    *,
    canvas_id: str,
    content: str,
    title: str | None = None,
) -> None:
    tool_name = await _discover_canvas_tool(
        user_token, CANVAS_UPDATE_TOOL_NAMES, keyword="update"
    )
    if not is_valid_canvas_id(canvas_id):
        raise SlackMcpError(f"Invalid canvas id: {canvas_id!r}")

    arguments: dict[str, Any] = {
        "canvas_id": canvas_id,
        "action": "replace",
        "content": content,
    }
    if title:
        arguments["title"] = title

    logger.info("Calling MCP tool %s for canvas %s", tool_name, canvas_id)
    await _mcp_request(
        user_token,
        "tools/call",
        {"name": tool_name, "arguments": arguments},
    )


async def _discover_draft_tool(user_token: str) -> str:
    result = await _mcp_request(user_token, "tools/list")
    tools = result.get("result", {}).get("tools", [])
    names = {tool.get("name", "") for tool in tools}
    for candidate in DRAFT_TOOL_NAMES:
        if candidate in names:
            return candidate
    for name in names:
        lowered = name.lower()
        if "draft" in lowered and "message" in lowered:
            return name
    raise SlackMcpError(
        f"No message draft tool found. Available tools: {sorted(names)}"
    )


async def send_channel_message_draft(
    user_token: str,
    *,
    channel_id: str,
    message: str,
    thread_ts: str | None = None,
) -> None:
    tool_name = await _discover_draft_tool(user_token)
    arguments: dict[str, Any] = {
        "channel_id": channel_id,
        "message": message,
    }
    if thread_ts:
        arguments["thread_ts"] = thread_ts

    logger.info("Calling MCP draft tool %s for channel %s", tool_name, channel_id)
    result = await _mcp_request(
        user_token,
        "tools/call",
        {"name": tool_name, "arguments": arguments},
    )
    tool_result = result.get("result", {})
    if tool_result.get("isError"):
        raise SlackMcpError(f"MCP draft tool error: {tool_result}")
