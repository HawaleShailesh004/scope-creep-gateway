from slack_bolt.async_app import AsyncApp

from .change_order_buttons import handle_open_change_order
from .draft_reply_buttons import handle_draft_reply
from .feedback_buttons import handle_feedback_button
from .payment_buttons import handle_simulate_payment
from .scope_creep_buttons import (
    handle_dismiss_creep,
    handle_gen_change_order,
    handle_let_it_slide,
)
from .setup_brief_buttons import handle_open_setup_brief
from .setup_brief_extract import handle_extract_setup_brief, handle_open_extracted_brief
from .update_brief_buttons import handle_open_update_brief
from listeners.commands.client_report import handle_show_client_report
from listeners.commands.studio_report import handle_show_studio_report


def register(app: AsyncApp):
    app.action("feedback")(handle_feedback_button)
    app.action("dismiss_creep")(handle_dismiss_creep)
    app.action("let_it_slide")(handle_let_it_slide)
    app.action("gen_change_order")(handle_gen_change_order)
    app.action("show_client_report")(handle_show_client_report)
    app.action("show_studio_report")(handle_show_studio_report)
    app.action("draft_reply")(handle_draft_reply)
    app.action("simulate_payment")(handle_simulate_payment)
    app.action("open_setup_brief")(handle_open_setup_brief)
    app.action("extract_setup_brief")(handle_extract_setup_brief)
    app.action("open_extracted_brief")(handle_open_extracted_brief)
    app.action("open_change_order")(handle_open_change_order)
    app.action("open_update_brief")(handle_open_update_brief)
