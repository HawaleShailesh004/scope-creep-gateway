from services.user_messages import APP_HOME_PRIVACY


def build_app_home_view(
    install_url: str | None = None, is_connected: bool = False
) -> dict:
    """Build the Scope Creep Gateway App Home view."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":shield: Scope Creep Gateway",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "Catch out-of-scope client requests *at the moment they happen* — "
                    "not at invoice time.\n\n"
                    "*In a project channel:*\n"
                    "• `/setup-brief` — define deliverables, budget, and client\n"
                    "• `/update-brief` — edit setup deliverables without a new channel\n"
                    "• `/change-order` — bill for additional work manually\n"
                    "• `/absorbed` — see goodwill work you've absorbed\n"
                    "• `/client-report` — pattern stats across projects\n"
                    "• `/studio-report` — studio capacity + billing summary\n"
                    "• `/scope-gateway-off` / `/scope-gateway-on` — pause or resume\n"
                    "• *Flag as scope change* — right-click any client message\n\n"
                    "Scope warnings are *private to the freelancer*. "
                    "Change orders and the Scope Health canvas are shared with the channel."
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": APP_HOME_PRIVACY,
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Scope Health* starts at 100% and decreases as change orders are added. "
                    "Open the *Canvas* tab in your project channel to see the live brief and change log."
                ),
            },
        },
        {"type": "divider"},
    ]

    if is_connected:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": ":large_green_circle: Slack MCP connected — canvas creation is enabled.",
                    }
                ],
            }
        )
    elif install_url:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f":red_circle: Connect Slack MCP for canvas features. "
                            f"<{install_url}|Connect now>"
                        ),
                    }
                ],
            }
        )
    else:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            ":red_circle: Set `SLACK_USER_TOKEN` for canvas create/update."
                        ),
                    }
                ],
            }
        )

    return {
        "type": "home",
        "blocks": blocks,
    }
