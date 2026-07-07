from __future__ import annotations

import json

from services.message_text import truncate_for_display
from services.user_messages import (
    ABSORB_CONFIRMED,
    DISMISS_SUCCESS,
    SCOPE_WARNING_BODY_INTRO,
    SCOPE_WARNING_NOT_IN_BRIEF,
    SCOPE_WARNING_PRIOR_MENTION,
    SCOPE_WARNING_REVISION_BODY,
    SCOPE_WARNING_TITLE,
)


def _button_value(
    *,
    change_order_id: str,
    channel_id: str,
    message_ts: str,
    project_id: str,
) -> str:
    return json.dumps(
        {
            "co_id": change_order_id,
            "ch": channel_id,
            "ts": message_ts,
            "pid": project_id,
        }
    )


def build_warning_blocks(
    *,
    client_message: str,
    new_task_summary: str | None,
    prior_mention_date: str | None,
    change_order_id: str,
    channel_id: str,
    message_ts: str,
    project_id: str,
    absorb_nudge: str | None = None,
    client_pattern_nudge: str | None = None,
    capacity_nudge: str | None = None,
    revision_deliverable: str | None = None,
    revision_limit: int | None = None,
) -> list[dict]:
    quoted = truncate_for_display(client_message)

    if revision_deliverable and revision_limit is not None:
        lines = [
            ":triangular_flag_on_post: *Revision limit reached*",
            "",
            SCOPE_WARNING_REVISION_BODY.format(
                quoted=quoted, deliverable=revision_deliverable
            ),
        ]
    else:
        lines = [
            f":triangular_flag_on_post: *{SCOPE_WARNING_TITLE}*",
            "",
            SCOPE_WARNING_BODY_INTRO.format(quoted=quoted),
            SCOPE_WARNING_NOT_IN_BRIEF,
        ]
        if new_task_summary:
            lines.append(f"_New work detected:_ {new_task_summary}")

    if prior_mention_date:
        lines.append(
            SCOPE_WARNING_PRIOR_MENTION.format(prior_mention_date=prior_mention_date)
        )
    if client_pattern_nudge:
        lines.append(client_pattern_nudge)
    if absorb_nudge:
        lines.append(absorb_nudge)
    if capacity_nudge:
        lines.append(capacity_nudge)

    button_value = _button_value(
        change_order_id=change_order_id,
        channel_id=channel_id,
        message_ts=message_ts,
        project_id=project_id,
    )

    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)},
        },
        {
            "type": "actions",
            "block_id": f"scope_warning_{change_order_id}",
            "elements": [
                {
                    "type": "button",
                    "action_id": "gen_change_order",
                    "text": {"type": "plain_text", "text": "Generate Change Order"},
                    "style": "primary",
                    "value": button_value,
                },
                {
                    "type": "button",
                    "action_id": "let_it_slide",
                    "text": {"type": "plain_text", "text": "Let it slide"},
                    "value": button_value,
                },
                {
                    "type": "button",
                    "action_id": "dismiss_creep",
                    "text": {"type": "plain_text", "text": "Not scope creep"},
                    "value": button_value,
                },
            ],
        },
        {
            "type": "actions",
            "block_id": f"scope_warning_draft_{change_order_id}",
            "elements": [
                {
                    "type": "button",
                    "action_id": "draft_reply",
                    "text": {"type": "plain_text", "text": "Draft the reply"},
                    "value": button_value,
                },
            ],
        },
    ]


def build_dismissed_blocks() -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":white_check_mark: *{DISMISS_SUCCESS}*",
            },
        }
    ]


def build_absorbed_blocks() -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":handshake: *{ABSORB_CONFIRMED}*",
            },
        }
    ]


def build_change_order_stub_blocks() -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    ":page_facing_up: *Change order flow* lands in Phase 4. "
                    "The flag is saved - you'll be able to draft and post a "
                    "change order from here next."
                ),
            },
        }
    ]
