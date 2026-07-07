from slack_bolt.async_app import AsyncApp

from listeners import actions, commands, events, middleware, shortcuts, views


def register_listeners(app: AsyncApp):
    middleware.register(app)
    actions.register(app)
    commands.register(app)
    events.register(app)
    shortcuts.register(app)
    views.register(app)
