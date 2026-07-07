from slack_bolt.async_app import AsyncApp

from .flag_scope_change import handle_flag_scope_change
from .import_brief import handle_import_brief


def register(app: AsyncApp):
    app.shortcut("flag_scope_change")(handle_flag_scope_change)
    app.shortcut("import_brief")(handle_import_brief)
