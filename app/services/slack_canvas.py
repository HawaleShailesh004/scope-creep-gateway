from __future__ import annotations

import asyncio
import logging
from typing import Any

from slack_sdk.web.async_client import AsyncWebClient

from services.slack_mcp import is_valid_canvas_id

logger = logging.getLogger(__name__)

RETRYABLE_ERRORS = frozenset({"edit_in_progress", "ratelimited", "rate_limited"})
DEFAULT_BACKOFFS = (0.5, 1.0, 2.0)


class SlackCanvasError(RuntimeError):
    pass


def _extract_error(response: dict) -> str:
    return str(response.get("error") or response)


async def _api_call_with_retry(
    client: AsyncWebClient,
    method: str,
    payload: dict,
    *,
    max_retries: int = 3,
) -> dict:
    last_error = ""
    for attempt in range(max_retries):
        response = await client.api_call(method, json=payload)
        if response.get("ok"):
            return response.data
        last_error = _extract_error(response)
        if last_error not in RETRYABLE_ERRORS or attempt >= max_retries - 1:
            raise SlackCanvasError(f"{method} failed: {last_error}")
        delay = DEFAULT_BACKOFFS[min(attempt, len(DEFAULT_BACKOFFS) - 1)]
        logger.warning("%s retry %s/%s after %s (%s)", method, attempt + 1, max_retries, delay, last_error)
        await asyncio.sleep(delay)
    raise SlackCanvasError(f"{method} failed: {last_error}")


async def lookup_section_id(
    user_token: str,
    *,
    canvas_id: str,
    contains_text: str,
    section_types: list[str] | None = None,
) -> str | None:
    if not is_valid_canvas_id(canvas_id):
        raise SlackCanvasError(f"Invalid canvas id: {canvas_id!r}")

    criteria: dict[str, Any] = {"contains_text": contains_text}
    if section_types:
        criteria["section_types"] = section_types

    client = AsyncWebClient(token=user_token)
    data = await _api_call_with_retry(
        client,
        "canvases.sections.lookup",
        {"canvas_id": canvas_id, "criteria": criteria},
    )
    sections = data.get("sections") or []
    if not sections:
        return None
    section_id = sections[0].get("id")
    return section_id if section_id else None


async def replace_canvas_markdown(
    user_token: str,
    *,
    canvas_id: str,
    content: str,
    title: str | None = None,
) -> None:
    if not is_valid_canvas_id(canvas_id):
        raise SlackCanvasError(f"Invalid canvas id: {canvas_id!r}")

    client = AsyncWebClient(token=user_token)
    await _api_call_with_retry(
        client,
        "canvases.edit",
        {
            "canvas_id": canvas_id,
            "changes": [
                {
                    "operation": "replace",
                    "document_content": {"type": "markdown", "markdown": content},
                }
            ],
        },
    )

    if title:
        await _api_call_with_retry(
            client,
            "canvases.edit",
            {
                "canvas_id": canvas_id,
                "changes": [
                    {
                        "operation": "rename",
                        "title_content": {"type": "markdown", "markdown": title},
                    }
                ],
            },
        )

    logger.info("Replaced full canvas %s", canvas_id)


async def replace_section_markdown(
    user_token: str,
    *,
    canvas_id: str,
    section_id: str,
    markdown: str,
) -> None:
    client = AsyncWebClient(token=user_token)
    await _api_call_with_retry(
        client,
        "canvases.edit",
        {
            "canvas_id": canvas_id,
            "changes": [
                {
                    "operation": "replace",
                    "section_id": section_id,
                    "document_content": {"type": "markdown", "markdown": markdown},
                }
            ],
        },
    )
    logger.info("Replaced canvas section %s on %s", section_id, canvas_id)


async def insert_after_section(
    user_token: str,
    *,
    canvas_id: str,
    section_id: str,
    markdown: str,
) -> None:
    client = AsyncWebClient(token=user_token)
    await _api_call_with_retry(
        client,
        "canvases.edit",
        {
            "canvas_id": canvas_id,
            "changes": [
                {
                    "operation": "insert_after",
                    "section_id": section_id,
                    "document_content": {"type": "markdown", "markdown": markdown},
                }
            ],
        },
    )
    logger.info("Inserted after section %s on canvas %s", section_id, canvas_id)


async def replace_section_by_anchor(
    user_token: str,
    *,
    canvas_id: str,
    anchor_text: str,
    markdown: str,
) -> bool:
    section_id = await lookup_section_id(
        user_token, canvas_id=canvas_id, contains_text=anchor_text
    )
    if not section_id:
        return False
    await replace_section_markdown(
        user_token, canvas_id=canvas_id, section_id=section_id, markdown=markdown
    )
    return True


# Backward-compatible alias used by existing call sites.
async def update_canvas_markdown(
    user_token: str,
    *,
    canvas_id: str,
    content: str,
    title: str | None = None,
) -> None:
    await replace_canvas_markdown(
        user_token, canvas_id=canvas_id, content=content, title=title
    )
