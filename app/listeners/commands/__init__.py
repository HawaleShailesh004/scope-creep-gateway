from slack_bolt.async_app import AsyncApp

from .absorbed_summary import register as register_absorbed
from .change_order import register as register_change_order
from .client_report import register as register_client_report
from .gateway_toggle import register as register_gateway_toggle
from .import_brief import register as register_import_brief
from .setup_brief import register as register_setup_brief
from .studio_report import register as register_studio_report
from .update_brief import register as register_update_brief


def register(app: AsyncApp):
    register_setup_brief(app)
    register_change_order(app)
    register_absorbed(app)
    register_client_report(app)
    register_studio_report(app)
    register_gateway_toggle(app)
    register_update_brief(app)
    register_import_brief(app)
