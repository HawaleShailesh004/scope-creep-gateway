from __future__ import annotations

import re

# Classifier input - keep head + tail for long pasted specs.
MAX_CLASSIFIER_MESSAGE_CHARS = 4_000

# Slack Block Kit section text limit is 3000; we stay under for quotes.
MAX_DISPLAY_QUOTE_CHARS = 280


def _text_from_rich_text_elements(elements: list) -> list[str]:
    parts: list[str] = []
    for element in elements:
        el_type = element.get("type")
        if el_type == "text":
            parts.append(element.get("text", ""))
        elif el_type == "link":
            parts.append(element.get("url", "") or element.get("text", ""))
        elif el_type == "user":
            parts.append(f"@{element.get('user_id', 'user')}")
        elif el_type in ("rich_text_section", "rich_text_quote", "rich_text_list"):
            parts.extend(_text_from_rich_text_elements(element.get("elements", [])))
        elif el_type == "rich_text_preformatted":
            parts.extend(_text_from_rich_text_elements(element.get("elements", [])))
    return parts


def _text_from_blocks(blocks: list) -> str:
    parts: list[str] = []
    for block in blocks or []:
        block_type = block.get("type")
        if block_type == "rich_text":
            parts.extend(_text_from_rich_text_elements(block.get("elements", [])))
        elif block_type == "section":
            text_obj = block.get("text") or {}
            if text_obj.get("type") == "mrkdwn":
                parts.append(text_obj.get("text", ""))
            elif text_obj.get("type") == "plain_text":
                parts.append(text_obj.get("text", ""))
    return " ".join(parts).strip()


def extract_message_text(event: dict) -> str:
    """Plain text from a Slack message event, including Block Kit fallbacks."""
    text = (event.get("text") or "").strip()
    if text:
        return _normalize_whitespace(text)

    blocks_text = _text_from_blocks(event.get("blocks") or [])
    if blocks_text:
        return _normalize_whitespace(blocks_text)

    attachments = event.get("attachments") or []
    for attachment in attachments:
        fallback = (attachment.get("fallback") or attachment.get("text") or "").strip()
        if fallback:
            return _normalize_whitespace(fallback)

    return ""


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def meaningful_word_count(text: str) -> int:
    """Count words that are not only URLs or emoji shortcuts."""
    if not text:
        return 0
    words = text.split()
    meaningful = 0
    for word in words:
        stripped = word.strip("<>@#")
        if not stripped:
            continue
        if stripped.startswith("http://") or stripped.startswith("https://"):
            continue
        if stripped.startswith(":") and stripped.endswith(":"):
            continue
        meaningful += 1
    return meaningful


def truncate_for_classifier(text: str, max_chars: int = MAX_CLASSIFIER_MESSAGE_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head - 20
    return f"{text[:head]}\n…[message truncated]…\n{text[-tail:]}"


def truncate_for_display(text: str, max_chars: int = MAX_DISPLAY_QUOTE_CHARS) -> str:
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    return stripped[: max_chars - 3] + "..."
