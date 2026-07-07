from slack_bolt.async_app import AsyncApp

from listeners.middleware.slash_command_log import register as register_slash_command_log


def register(app: AsyncApp) -> None:
    register_slash_command_log(app)
