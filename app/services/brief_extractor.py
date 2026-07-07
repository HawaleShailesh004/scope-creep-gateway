from __future__ import annotations

import base64
import json
import logging
import os
import re

import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None

CLASSIFIABLE = frozenset({"png", "jpg", "jpeg", "gif", "webp", "pdf"})


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY must be set in .env")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def pick_scope_document_file(files: list[dict]) -> dict | None:
    for file_obj in files or []:
        if (file_obj.get("filetype") or "").lower() in CLASSIFIABLE:
            return file_obj
    return None


def _media_type(file_obj: dict) -> str:
    filetype = (file_obj.get("filetype") or "png").lower()
    if filetype == "pdf":
        return "application/pdf"
    if filetype == "jpg":
        return "image/jpeg"
    return f"image/{filetype}"


def extract_brief_from_document(
    *,
    file_bytes: bytes,
    media_type: str,
    caption: str = "",
) -> dict:
    """Vision OCR/extract for setup-brief prefill. Returns structured fields."""
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

    user = f"""Extract the project scope from this document (SOW, contract screenshot, or brief).

Caption from uploader: "{caption or "none"}"

Return ONLY strict JSON:
{{
  "project_name": "string",
  "deliverables": ["one per line items from in-scope section"],
  "budget": number or null,
  "currency": "INR or other ISO code",
  "deadline": "YYYY-MM-DD or null",
  "revision_limit": integer or null,
  "client_label": "company or client name or null"
}}

Use null for fields you cannot read. Deliverables should be concise bullet labels."""

    resp = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [content_block, {"type": "text", "text": user}],
            }
        ],
    )
    text = resp.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    data = json.loads(text)
    if not isinstance(data.get("deliverables"), list):
        data["deliverables"] = []
    return data
