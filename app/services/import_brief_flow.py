from __future__ import annotations

import logging
from typing import Any

from listeners.views.setup_brief_modal import build_setup_brief_modal
from services.brief_extractor import extract_brief_from_document, pick_scope_document_file
from services.mockup_classifier import _download_file, _media_type
from services.slack_modals import open_view_with_trigger

logger = logging.getLogger(__name__)


def _format_budget(value: Any) -> str | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number == int(number):
        return str(int(number))
    return str(number)


def _prefill_from_extracted(data: dict) -> dict[str, str | list[str] | None]:
    deliverables = [
        str(item).strip()
        for item in (data.get("deliverables") or [])
        if str(item).strip()
    ]
    revision = data.get("revision_limit")
    revision_limit = str(revision) if revision is not None else None
    return {
        "project_name": (data.get("project_name") or "").strip() or None,
        "deliverables": deliverables or None,
        "budget": _format_budget(data.get("budget")),
        "deadline": (data.get("deadline") or None),
        "client_label": (data.get("client_label") or None),
        "revision_limit": revision_limit,
    }


async def open_prefilled_setup_modal(
    client,
    *,
    trigger_id: str,
    ack,
    channel_id: str,
    team_id: str,
    freelancer_id: str,
    extracted: dict,
) -> bool:
    prefill = _prefill_from_extracted(extracted)
    view = build_setup_brief_modal(
        channel_id=channel_id,
        team_id=team_id,
        freelancer_id=freelancer_id,
        project_name=prefill["project_name"],
        deliverables=prefill["deliverables"],
        budget=prefill["budget"],
        deadline=prefill["deadline"],
        client_label=prefill["client_label"],
        revision_limit=prefill["revision_limit"],
    )
    return bool(
        await open_view_with_trigger(
            client,
            trigger_id=trigger_id,
            view=view,
            ack=ack,
        )
    )


async def extract_brief_from_message(
    *,
    bot_token: str,
    message: dict,
) -> dict | None:
    file_obj = pick_scope_document_file(message.get("files") or [])
    if not file_obj or not file_obj.get("url_private"):
        return None
    try:
        file_bytes = await _download_file(file_obj["url_private"], bot_token)
        caption = (message.get("text") or file_obj.get("title") or "").strip()
        return extract_brief_from_document(
            file_bytes=file_bytes,
            media_type=_media_type(file_obj),
            caption=caption,
        )
    except Exception as exc:
        logger.exception("import_brief_extract_failed: %s", exc)
        return None
