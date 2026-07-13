"""Single switch for local vs production Slack routing.

Set in .env:
    APP_MODE=dev     # local Socket Mode
    APP_MODE=prod    # Railway HTTP

Or run:
    python scripts/switch_mode.py dev
    python scripts/switch_mode.py prod
"""

from __future__ import annotations

import os
from dataclasses import dataclass

RAILWAY_SLACK_EVENTS_URL = (
    "https://scope-creep-gateway-production.up.railway.app/slack/events"
)

VALID_MODES = frozenset({"dev", "prod"})


@dataclass(frozen=True)
class AppMode:
    name: str  # "dev" | "prod"
    transport: str  # "socket" | "http"

    @property
    def is_dev(self) -> bool:
        return self.name == "dev"

    @property
    def is_prod(self) -> bool:
        return self.name == "prod"


def resolve_app_mode() -> AppMode:
    """Resolve APP_MODE, with safe fallbacks for Railway (PORT) and legacy env."""
    raw = os.environ.get("APP_MODE", "").strip().lower()
    if raw in VALID_MODES:
        transport = "socket" if raw == "dev" else "http"
        return AppMode(name=raw, transport=transport)

    # Legacy overrides
    explicit = os.environ.get("SLACK_TRANSPORT", "").strip().lower()
    if explicit in ("socket", "http"):
        return AppMode(
            name="dev" if explicit == "socket" else "prod",
            transport=explicit,
        )

    # Railway / PaaS sets PORT → production HTTP
    if os.environ.get("PORT"):
        return AppMode(name="prod", transport="http")

    # Default for laptop: local Socket Mode
    return AppMode(name="dev", transport="socket")


def apply_mode(mode: AppMode) -> None:
    """Force transport env so the rest of the app stays consistent."""
    os.environ["APP_MODE"] = mode.name
    os.environ["SLACK_TRANSPORT"] = mode.transport


def mode_banner(mode: AppMode) -> str:
    if mode.is_dev:
        return (
            "\n"
            "============================================================\n"
            "  APP_MODE = DEV  ->  LOCAL Socket Mode\n"
            "  Slack traffic must come to THIS process.\n"
            "  Checklist:\n"
            "    1. Pause / stop Railway\n"
            "    2. Slack app -> Socket Mode = ON\n"
            "    3. python app.py  (this process)\n"
            "============================================================"
        )
    return (
        "\n"
        "============================================================\n"
        "  APP_MODE = PROD  ->  Railway HTTP\n"
        f"  Expected URL: {RAILWAY_SLACK_EVENTS_URL}\n"
        "  Checklist:\n"
        "    1. Stop local python app.py\n"
        "    2. Railway service running\n"
        "    3. Slack app -> Socket Mode = OFF\n"
        "    4. Event + Interactivity Request URL = Railway\n"
        "============================================================"
    )
