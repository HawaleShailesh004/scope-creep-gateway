from slack_bolt.async_app import AsyncApp

from .app_home_opened import handle_app_home_opened
from .app_mentioned import handle_app_mentioned
from .member_joined import register as register_member_joined
from .message import handle_message


def register(app: AsyncApp):
    app.event("app_home_opened")(handle_app_home_opened)
    app.event("app_mention")(handle_app_mentioned)
    app.event("message")(handle_message)
    register_member_joined(app)
