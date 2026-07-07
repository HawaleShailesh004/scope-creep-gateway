import asyncio

import json

import logging



from slack_bolt import Ack

from slack_sdk.web.async_client import AsyncWebClient



from listeners.views.warning_card import build_absorbed_blocks, build_dismissed_blocks

from services.absorbed import log_absorbed

from services.change_order_flow import open_change_order_modal

from services.change_orders import get_change_order

from services.operation_locks import LockKeys, is_locked, release, try_acquire

from services.scope_warnings import dismiss_scope_flag

from services.slack_modals import notify_trigger_expired

from services.user_messages import (

    ABSORB_CONFIRMED,

    CHANGE_ORDER_FORM_OPENING,

    DISMISS_FAILED,

    DISMISS_SUCCESS,

    LEGACY_WARNING_BUTTON,

    TRIGGER_EXPIRED_CHANGE_ORDER,

)



logger = logging.getLogger(__name__)





def _parse_action_value(body: dict) -> dict:

    return json.loads(body["actions"][0]["value"])





async def handle_dismiss_creep(

    ack: Ack,

    body: dict,

    respond,

    client: AsyncWebClient,

    logger: logging.Logger,

):

    await ack()



    try:

        payload = _parse_action_value(body)

        change_order_id = payload["co_id"]

        await asyncio.to_thread(dismiss_scope_flag, change_order_id)



        await respond(

            replace_original=True,

            text=DISMISS_SUCCESS,

            blocks=build_dismissed_blocks(),

        )

        logger.info("scope_warning_dismissed change_order_id=%s", change_order_id)

    except Exception as exc:

        logger.exception("Failed to dismiss scope warning: %s", exc)

        user_id = body.get("user", {}).get("id")

        channel_id = body.get("channel", {}).get("id")

        if user_id and channel_id:

            await client.chat_postEphemeral(

                channel=channel_id,

                user=user_id,

                text=DISMISS_FAILED,

            )





async def handle_let_it_slide(

    ack: Ack,

    body: dict,

    respond,

    client: AsyncWebClient,

    logger: logging.Logger,

):

    await ack()



    try:

        payload = _parse_action_value(body)

        change_order_id = payload["co_id"]



        change_order = await asyncio.to_thread(get_change_order, change_order_id)

        if not change_order:

            return



        await asyncio.to_thread(

            log_absorbed,

            project_id=change_order["project_id"],

            client_id=change_order.get("client_id"),

            trigger_message_ts=change_order.get("trigger_message_ts"),

            trigger_text=change_order.get("trigger_text"),

            task_summary=change_order.get("task_description"),

            estimated_value=float(change_order.get("estimated_value") or 0),

            estimated_hours=float(change_order.get("estimated_hours") or 0) or None,

            size=change_order.get("size"),

            source="manual",

        )

        await asyncio.to_thread(dismiss_scope_flag, change_order_id)



        await respond(

            replace_original=True,

            text=ABSORB_CONFIRMED,

            blocks=build_absorbed_blocks(),

        )

        logger.info("scope_warning_absorbed change_order_id=%s", change_order_id)

    except Exception as exc:

        logger.exception("Failed to absorb scope warning: %s", exc)





async def handle_gen_change_order(

    ack: Ack,

    body: dict,

    client: AsyncWebClient,

    logger: logging.Logger,

):

    payload = _parse_action_value(body)

    change_order_id = payload["co_id"]

    channel_id = payload["ch"]

    thread_ts = payload["ts"]

    user_id = body["user"]["id"]

    project_id = payload.get("pid")



    if not project_id:

        await ack()

        await client.chat_postEphemeral(

            channel=channel_id,

            user=user_id,

            text=LEGACY_WARNING_BUTTON,

        )

        return



    draft_key = LockKeys.draft(change_order_id)

    if is_locked(draft_key):

        await ack()

        await client.chat_postEphemeral(

            channel=channel_id,

            user=user_id,

            text=CHANGE_ORDER_FORM_OPENING,

        )

        return



    if not try_acquire(draft_key, ttl_seconds=60):

        await ack()

        await client.chat_postEphemeral(

            channel=channel_id,

            user=user_id,

            text=CHANGE_ORDER_FORM_OPENING,

        )

        return



    try:

        opened = await open_change_order_modal(

            client,

            trigger_id=body["trigger_id"],

            ack=ack,

            change_order_id=change_order_id,

            channel_id=channel_id,

            thread_ts=thread_ts,

            project_id=project_id,

        )

    finally:

        release(draft_key)



    if not opened:

        await notify_trigger_expired(

            client,

            channel_id=channel_id,

            user_id=user_id,

            text=TRIGGER_EXPIRED_CHANGE_ORDER,

        )

