import json

CALLBACK_ID = "setup_brief_submit"


def _text_input(*, action_id: str, placeholder: str, multiline: bool = False, initial: str | None = None) -> dict:
    element: dict = {
        "type": "plain_text_input",
        "action_id": action_id,
        "placeholder": {"type": "plain_text", "text": placeholder},
    }
    if multiline:
        element["multiline"] = True
    if initial:
        element["initial_value"] = initial
    return element


def _client_user_element(client_slack_id: str | None = None) -> dict:
    element: dict = {
        "type": "users_select",
        "action_id": "client_user",
        "placeholder": {"type": "plain_text", "text": "Select the client"},
    }
    if client_slack_id:
        element["initial_user"] = client_slack_id
    return element


def build_setup_brief_modal(
    *,
    channel_id: str,
    team_id: str,
    freelancer_id: str,
    project_name: str | None = None,
    deliverables: list[str] | None = None,
    budget: str | None = None,
    deadline: str | None = None,
    client_label: str | None = None,
    revision_limit: str | None = None,
    exclusions: list[str] | None = None,
    client_slack_id: str | None = None,
    status_note: str | None = None,
) -> dict:
    deliverables_text = "\n".join(deliverables) if deliverables else None
    exclusions_text = "\n".join(exclusions) if exclusions else None
    deadline_element: dict = {
        "type": "datepicker",
        "action_id": "deadline",
        "placeholder": {"type": "plain_text", "text": "Select a date"},
    }
    if deadline:
        deadline_element["initial_date"] = deadline

    input_blocks = [
            {
                "type": "input",
                "block_id": "project_name_block",
                "label": {"type": "plain_text", "text": "Project name"},
                "element": _text_input(
                    action_id="project_name",
                    placeholder="Acme redesign",
                    initial=project_name,
                ),
            },
            {
                "type": "input",
                "block_id": "deliverables_block",
                "label": {"type": "plain_text", "text": "Deliverables (one per line)"},
                "element": _text_input(
                    action_id="deliverables",
                    placeholder="Homepage redesign\nAbout page\nContact form",
                    multiline=True,
                    initial=deliverables_text,
                ),
            },
            {
                "type": "input",
                "block_id": "budget_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "Budget (INR)"},
                "element": _text_input(
                    action_id="budget",
                    placeholder="50000",
                    initial=budget,
                ),
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
                "block_id": "exclusions_block",
                "optional": True,
                "label": {
                    "type": "plain_text",
                    "text": "Explicitly out of scope (one per line)",
                },
                "element": _text_input(
                    action_id="exclusions",
                    placeholder="Blog section\nE-commerce checkout",
                    multiline=True,
                    initial=exclusions_text,
                ),
            },
            {
                "type": "input",
                "block_id": "client_user_block",
                "label": {"type": "plain_text", "text": "Client"},
                "element": _client_user_element(client_slack_id),
            },
            {
                "type": "input",
                "block_id": "client_label_block",
                "optional": True,
                "label": {"type": "plain_text", "text": "Client label (optional)"},
                "element": _text_input(
                    action_id="client_label",
                    placeholder="Acme Corp",
                    initial=client_label,
                ),
            },
            {
                "type": "input",
                "block_id": "revision_limit_block",
                "optional": True,
                "label": {
                    "type": "plain_text",
                    "text": "Default revision rounds per deliverable",
                },
                "element": _text_input(
                    action_id="revision_limit",
                    placeholder="2",
                    initial=revision_limit,
                ),
            },
    ]

    blocks: list[dict] = []
    if status_note:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": status_note},
            }
        )
        blocks.append({"type": "divider"})
    blocks.extend(input_blocks)

    return {
        "type": "modal",
        "callback_id": CALLBACK_ID,
        "private_metadata": json.dumps(
            {
                "channel_id": channel_id,
                "team_id": team_id,
                "freelancer_id": freelancer_id,
            }
        ),
        "title": {"type": "plain_text", "text": "Project Brief"},
        "submit": {"type": "plain_text", "text": "Create brief"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks,
    }
