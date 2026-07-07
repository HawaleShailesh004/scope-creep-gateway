import json

CALLBACK_ID = "update_brief_submit"


def build_update_brief_modal(
    *,
    channel_id: str,
    project_id: str,
    freelancer_id: str,
    project_name: str,
    deliverables: list[str],
    budget: str | None,
    deadline: str | None,
    revision_limit: str | None,
) -> dict:
    deliverable_text = "\n".join(deliverables)
    deadline_element: dict = {
        "type": "datepicker",
        "action_id": "deadline",
    }
    if deadline:
        deadline_element["initial_date"] = deadline

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "_Change-order deliverables are preserved automatically. "
                    "Edit the original setup items below._"
                ),
            },
        },
        {
            "type": "input",
            "block_id": "project_name_block",
            "label": {"type": "plain_text", "text": "Project name"},
            "element": {
                "type": "plain_text_input",
                "action_id": "project_name",
                "initial_value": project_name,
            },
        },
        {
            "type": "input",
            "block_id": "deliverables_block",
            "label": {"type": "plain_text", "text": "Setup deliverables (one per line)"},
            "element": {
                "type": "plain_text_input",
                "action_id": "deliverables",
                "multiline": True,
                "initial_value": deliverable_text,
            },
        },
        {
            "type": "input",
            "block_id": "budget_block",
            "optional": True,
            "label": {"type": "plain_text", "text": "Budget (INR)"},
            "element": {
                "type": "plain_text_input",
                "action_id": "budget",
                "initial_value": budget or "",
            },
        },
        {
            "type": "input",
            "block_id": "deadline_block",
            "optional": True,
            "label": {"type": "plain_text", "text": "Deadline"},
            "element": deadline_element,
        },
        {
            "type": "input",
            "block_id": "revision_limit_block",
            "optional": True,
            "label": {
                "type": "plain_text",
                "text": "Default revision rounds per setup deliverable",
            },
            "element": {
                "type": "plain_text_input",
                "action_id": "revision_limit",
                "initial_value": revision_limit or "",
            },
        },
    ]

    return {
        "type": "modal",
        "callback_id": CALLBACK_ID,
        "private_metadata": json.dumps(
            {
                "channel_id": channel_id,
                "project_id": project_id,
                "freelancer_id": freelancer_id,
            }
        ),
        "title": {"type": "plain_text", "text": "Update Brief"},
        "submit": {"type": "plain_text", "text": "Save changes"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks,
    }
