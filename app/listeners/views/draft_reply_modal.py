from __future__ import annotations

import json

CALLBACK_ID = "draft_reply_submit"
POST_CALLBACK_ID = "draft_reply_post_submit"

# Slack plain_text_input initial_value limit
_MAX_REPLY_CHARS = 3000


def build_draft_reply_modal(
    *,
    change_order_id: str,
    channel_id: str,
    project_id: str,
    thread_ts: str | None = None,
) -> dict:
    return {
        "type": "modal",
        "callback_id": CALLBACK_ID,
        "private_metadata": json.dumps(
            {
                "change_order_id": change_order_id,
                "channel_id": channel_id,
                "project_id": project_id,
                "thread_ts": thread_ts or "",
            }
        ),
        "title": {"type": "plain_text", "text": "Draft the reply"},
        "submit": {"type": "plain_text", "text": "Generate"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "Pick a tone. We'll draft a client-facing message you can "
                        "edit and post - *nothing is sent until you click Post*."
                    ),
                },
            },
            {
                "type": "input",
                "block_id": "tone_block",
                "label": {"type": "plain_text", "text": "Tone"},
                "element": {
                    "type": "static_select",
                    "action_id": "tone",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "Neutral"},
                        "value": "neutral",
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Warm"},
                            "value": "warm",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Neutral"},
                            "value": "neutral",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Firm"},
                            "value": "firm",
                        },
                    ],
                },
            },
        ],
    }


def build_draft_reply_result_modal(
    *,
    reply_text: str,
    tone: str,
    channel_id: str,
    thread_ts: str | None,
    change_order_id: str,
) -> dict:
    trimmed = reply_text[:_MAX_REPLY_CHARS]
    truncated_note = ""
    if len(reply_text) > _MAX_REPLY_CHARS:
        truncated_note = "\n\n_(Draft was trimmed to fit - finish editing in the field below.)_"

    return {
        "type": "modal",
        "callback_id": POST_CALLBACK_ID,
        "private_metadata": json.dumps(
            {
                "channel_id": channel_id,
                "thread_ts": thread_ts or "",
                "change_order_id": change_order_id,
                "tone": tone,
            }
        ),
        "title": {"type": "plain_text", "text": "Edit & post reply"},
        "submit": {"type": "plain_text", "text": "Post to channel"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Tone: {tone.title()}* - edit the message below, "
                        f"then post when you're happy with it.{truncated_note}"
                    ),
                },
            },
            {
                "type": "input",
                "block_id": "reply_block",
                "label": {"type": "plain_text", "text": "Client-facing message"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reply_text",
                    "multiline": True,
                    "initial_value": trimmed,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            "_Posts to this project channel"
                            + (" in the client thread" if thread_ts else "")
                            + " when you click *Post to channel*._"
                        ),
                    }
                ],
            },
        ],
    }


def build_draft_reply_posted_modal() -> dict:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Posted"},
        "close": {"type": "plain_text", "text": "Done"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":white_check_mark: *Your reply was posted to the channel.*\n\n"
                        "You can still edit or follow up in Slack if needed."
                    ),
                },
            }
        ],
    }
