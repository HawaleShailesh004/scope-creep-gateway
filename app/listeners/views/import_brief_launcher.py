import json


def build_import_brief_launcher_blocks(*, channel_id: str, team_id: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Import a scope document* (SOW, contract, or brief screenshot) "
                    "into the setup form.\n\n"
                    "1. Upload the document to this channel\n"
                    "2. Open the message menu → *Import brief from document*\n\n"
                    "Or open the form manually below."
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open project brief form"},
                    "style": "primary",
                    "action_id": "open_setup_brief",
                    "value": json.dumps(
                        {"channel_id": channel_id, "team_id": team_id}
                    ),
                }
            ],
        },
    ]
