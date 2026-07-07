import json


def build_update_brief_launcher_blocks(*, channel_id: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Update the project brief* for this channel.\n"
                    "Click below to open the editor. Only you can see this message."
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open brief editor"},
                    "style": "primary",
                    "action_id": "open_update_brief",
                    "value": json.dumps({"channel_id": channel_id}),
                }
            ],
        },
    ]
