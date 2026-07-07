from __future__ import annotations

import base64
import json
import logging
import os
import re

import anthropic
import httpx

from services.brief_template import format_budget
from services.message_text import extract_message_text

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None

CLASSIFIABLE_FILE_TYPES = frozenset({"png", "jpg", "jpeg", "gif", "webp", "pdf"})
_REQUEST_HINTS = re.compile(
    r"\b(mockup|design|attached|attachment|wireframe|screenshot|see this|layout|prototype)\b",
    re.I,
)


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY must be set in .env")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def pick_classifiable_file(event: dict) -> dict | None:
    for file_obj in event.get("files") or []:
        filetype = (file_obj.get("filetype") or "").lower()
        if filetype in CLASSIFIABLE_FILE_TYPES:
            return file_obj
    return None


def is_mockup_work_request(event: dict) -> bool:
    """Cost guard — only vision when the message looks like a work request."""
    text = extract_message_text(event)
    if meaningful_word_count(text) >= 3:
        return True
    if _REQUEST_HINTS.search(text):
        return True
    file_obj = pick_classifiable_file(event)
    if file_obj:
        name = (file_obj.get("name") or file_obj.get("title") or "").lower()
        if _REQUEST_HINTS.search(name):
            return True
    return False


def meaningful_word_count(text: str) -> int:
    from services.message_text import meaningful_word_count as _count

    return _count(text)


async def _download_file(url_private: str, bot_token: str) -> bytes:
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            url_private,
            headers={"Authorization": f"Bearer {bot_token}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.content


def _media_type(file_obj: dict) -> str:
    filetype = (file_obj.get("filetype") or "png").lower()
    if filetype == "pdf":
        return "application/pdf"
    if filetype == "jpg":
        return "image/jpeg"
    return f"image/{filetype}"


def classify_mockup(
    *,
    brief_markdown: str,
    deliverables: list[str],
    file_bytes: bytes,
    media_type: str,
    caption: str,
) -> dict:
    """Vision compare mockup against brief; returns classifier-shaped JSON."""
    encoded = base64.standard_b64encode(file_bytes).decode("ascii")
    if media_type == "application/pdf":
        content_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": encoded,
            },
        }
    else:
        content_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": encoded,
            },
        }

    user = f"""PROJECT BRIEF:
{brief_markdown}

IN-SCOPE DELIVERABLES:
{chr(10).join("- " + d for d in deliverables)}

CLIENT MESSAGE / CAPTION:
"{caption or "See attached mockup/design."}"

Compare the attached file to the agreed brief. Flag elements in the mockup that are NOT in scope.

Return ONLY strict JSON:
{{"verdict": "IN_SCOPE|OUT_OF_SCOPE|AMBIGUOUS",
 "confidence": 0.0-1.0,
 "size": "trivial|small|significant|major",
 "estimated_value": 0,
 "estimated_hours": 0,
 "is_revision_request": false,
 "target_deliverable": null,
 "matched_deliverable": null,
 "new_task_summary": "short label for out-of-scope elements, else null",
 "rationale": "one sentence citing specific out-of-scope elements"}}"""

    resp = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [content_block, {"type": "text", "text": user}],
            }
        ],
    )
    text = resp.content[0].text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    result = json.loads(text)
    result.setdefault("size", "significant")
    result.setdefault("estimated_value", 0)
    result.setdefault("estimated_hours", 0)
    result.setdefault("is_revision_request", False)
    return result


async def classify_mockup_from_event(
    bot_token: str,
    event: dict,
    *,
    brief_markdown: str,
    deliverables: list[str],
) -> dict | None:
    file_obj = pick_classifiable_file(event)
    if not file_obj or not file_obj.get("url_private"):
        return None

    try:
        file_bytes = await _download_file(file_obj["url_private"], bot_token)
        caption = extract_message_text(event) or file_obj.get("title") or ""
        return classify_mockup(
            brief_markdown=brief_markdown,
            deliverables=deliverables,
            file_bytes=file_bytes,
            media_type=_media_type(file_obj),
            caption=caption,
        )
    except Exception as exc:
        logger.exception("mockup_classify_failed: %s", exc)
        return None
