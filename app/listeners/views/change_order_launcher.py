import json


def build_change_order_launcher_blocks(*, channel_id: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Create a change order* for additional work on this project.\n"
                    "Click below to open the form. Only you can see this message."
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open change order form"},
                    "style": "primary",
                    "action_id": "open_change_order",
                    "value": json.dumps({"channel_id": channel_id}),
                }
            ],
        },
    ]
