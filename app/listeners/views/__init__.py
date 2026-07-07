from slack_bolt.async_app import AsyncApp

from .change_order_submit import register as register_change_order_submit
from .draft_reply_post_submit import register as register_draft_reply_post_submit
from .draft_reply_submit import register as register_draft_reply_submit
from .update_brief_submit import register as register_update_brief_submit


def register(app: AsyncApp):
    register_change_order_submit(app)
    register_draft_reply_submit(app)
    register_draft_reply_post_submit(app)
    register_update_brief_submit(app)
