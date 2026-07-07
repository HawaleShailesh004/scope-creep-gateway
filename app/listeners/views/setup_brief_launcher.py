import json

from listeners.views.setup_brief_modal import build_setup_brief_modal
from services.setup_brief_draft_cache import assess_extracted_brief, prefill_from_extracted
from services.user_messages import (
    EXTRACT_MODAL_EMPTY,
    EXTRACT_MODAL_FAILED,
    EXTRACT_MODAL_INSUFFICIENT,
    EXTRACT_MODAL_PARTIAL,
    EXTRACT_MODAL_STILL_NEED_CLIENT,
)


def build_setup_brief_launcher_blocks(*, channel_id: str, team_id: str) -> list[dict]:
    meta = json.dumps({"channel_id": channel_id, "team_id": team_id})
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Set up the project brief* for this channel.\n"
                    "Draft from your kickoff chat, or fill it in yourself. "
                    "Only you can see this message."
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Draft from conversation"},
                    "style": "primary",
                    "action_id": "extract_setup_brief",
                    "value": meta,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Fill it in myself"},
                    "action_id": "open_setup_brief",
                    "value": meta,
                },
            ],
        },
    ]


def _status_note_for_extract(extracted: dict | None, *, empty_channel: bool = False) -> str:
    if empty_channel:
        return EXTRACT_MODAL_EMPTY
    if not extracted:
        return EXTRACT_MODAL_FAILED
    quality = assess_extracted_brief(extracted)
    missing = ", ".join(quality["missing"])
    if quality["tier"] == "insufficient":
        return EXTRACT_MODAL_INSUFFICIENT.format(missing=missing)
    if quality["tier"] == "partial":
        return EXTRACT_MODAL_PARTIAL.format(missing=missing)
    return EXTRACT_MODAL_STILL_NEED_CLIENT


def build_manual_brief_modal(
    *,
    channel_id: str,
    team_id: str,
    freelancer_id: str,
    extracted: dict | None = None,
    status_note: str | None = None,
    empty_channel: bool = False,
) -> dict:
    prefill = prefill_from_extracted(extracted) if extracted else {}
    note = status_note or _status_note_for_extract(extracted, empty_channel=empty_channel)
    return build_setup_brief_modal(
        channel_id=channel_id,
        team_id=team_id,
        freelancer_id=freelancer_id,
        project_name=prefill.get("project_name"),
        deliverables=prefill.get("deliverables"),
        exclusions=prefill.get("exclusions"),
        budget=prefill.get("budget"),
        deadline=prefill.get("deadline"),
        client_label=prefill.get("client_label"),
        revision_limit=prefill.get("revision_limit"),
        client_slack_id=prefill.get("client_slack_id"),
        status_note=note,
    )
