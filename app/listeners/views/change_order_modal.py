from __future__ import annotations

import json

CALLBACK_ID = "change_order_submit"


def _modal_metadata(
    *,
    change_order_id: str,
    channel_id: str,
    thread_ts: str,
    project_id: str,
) -> str:
    return json.dumps(
        {
            "change_order_id": change_order_id,
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "project_id": project_id,
        }
    )


def build_bootstrap_loading_modal(
    *,
    channel_id: str,
    user_id: str,
    thread_ts: str = "",
    message_ts: str | None = None,
    message_text: str | None = None,
    source: str,
) -> dict:
    """Loading shell opened before any DB work; bootstrap fills the real form."""
    return {
        "type": "modal",
        "callback_id": CALLBACK_ID,
        "private_metadata": json.dumps(
            {
                "bootstrap": True,
                "source": source,
                "channel_id": channel_id,
                "user_id": user_id,
                "thread_ts": thread_ts,
                "message_ts": message_ts,
                "message_text": message_text,
            }
        ),
        "title": {"type": "plain_text", "text": "Change Order"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":hourglass_flowing_sand: Preparing change order… "
                        "This usually takes a few seconds."
                    ),
                },
            }
        ],
    }


def build_loading_change_order_modal(
    *,
    change_order_id: str,
    channel_id: str,
    thread_ts: str,
    project_id: str,
) -> dict:
    """Opens within Slack's 3s trigger_id window; filled via views.update after drafting."""
    return {
        "type": "modal",
        "callback_id": CALLBACK_ID,
        "private_metadata": _modal_metadata(
            change_order_id=change_order_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            project_id=project_id,
        ),
        "title": {"type": "plain_text", "text": "Change Order"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":hourglass_flowing_sand: ScopeGuard is drafting a change order… "
                        "This usually takes a few seconds."
                    ),
                },
            }
        ],
    }


def build_change_order_error_modal(message: str) -> dict:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Change Order"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":warning: {message}"},
            }
        ],
    }


def build_change_order_modal(
    *,
    change_order_id: str,
    channel_id: str,
    thread_ts: str,
    project_id: str,
    draft: dict,
) -> dict:
    cost = draft.get("estimated_cost", "")
    days = draft.get("timeline_impact_days", "")
    description = draft.get("task_description", "")

    return {
        "type": "modal",
        "callback_id": CALLBACK_ID,
        "private_metadata": _modal_metadata(
            change_order_id=change_order_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            project_id=project_id,
        ),
        "title": {"type": "plain_text", "text": "Change Order"},
        "submit": {"type": "plain_text", "text": "Post to channel"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "task_block",
                "label": {"type": "plain_text", "text": "Task description"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "task_description",
                    "multiline": True,
                    "initial_value": str(description)[:2800],
                },
            },
            {
                "type": "input",
                "block_id": "cost_block",
                "label": {"type": "plain_text", "text": "Additional cost (INR)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "estimated_cost",
                    "initial_value": str(cost),
                },
            },
            {
                "type": "input",
                "block_id": "days_block",
                "label": {"type": "plain_text", "text": "Timeline impact (days)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "timeline_impact_days",
                    "initial_value": str(days),
                },
            },
        ],
    }
