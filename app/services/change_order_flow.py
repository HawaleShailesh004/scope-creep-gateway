from __future__ import annotations

import asyncio
import logging

from slack_sdk.web.async_client import AsyncWebClient

from listeners.views.change_order_modal import (
    build_bootstrap_loading_modal,
    build_change_order_error_modal,
    build_change_order_modal,
    build_loading_change_order_modal,
)
from services.change_order_drafter import draft_change_order
from services.change_orders import get_change_order, proposed_cost_total
from services.project_context import load_project_by_channel
from services.operation_locks import LockKeys, is_locked, release, try_acquire
from services.scope_warnings import (
    create_manual_scope_flag,
    flag_already_exists,
)
from services.slack_modals import open_view_with_trigger
from services.user_messages import (
    CO_ERROR_ALREADY_POSTED,
    CO_ERROR_BOOTSTRAP_BUSY,
    CO_ERROR_DISMISSED,
    CO_ERROR_DRAFT_FAILED,
    CO_ERROR_FLAG_EXISTS,
    CO_ERROR_FREELANCER_ONLY,
    CO_ERROR_NO_MESSAGE_TEXT,
    CO_ERROR_NO_PROJECT,
    CO_ERROR_NOT_FOUND,
    CO_ERROR_PREPARE_FAILED,
)

logger = logging.getLogger(__name__)


async def _fill_change_order_modal(
    client: AsyncWebClient,
    *,
    view_id: str,
    view_hash: str,
    change_order_id: str,
    channel_id: str,
    thread_ts: str,
    project_id: str,
) -> None:
    try:
        change_order = await asyncio.to_thread(get_change_order, change_order_id)
        if not change_order:
            await client.views_update(
                view_id=view_id,
                hash=view_hash,
                view=build_change_order_error_modal(CO_ERROR_NOT_FOUND),
            )
            return
        if change_order.get("status") == "dismissed":
            await client.views_update(
                view_id=view_id,
                hash=view_hash,
                view=build_change_order_error_modal(CO_ERROR_DISMISSED),
            )
            return
        if change_order.get("status") in ("proposed", "paid"):
            await client.views_update(
                view_id=view_id,
                hash=view_hash,
                view=build_change_order_error_modal(CO_ERROR_ALREADY_POSTED),
            )
            return

        context = await asyncio.to_thread(load_project_by_channel, channel_id)
        if not context:
            await client.views_update(
                view_id=view_id,
                hash=view_hash,
                view=build_change_order_error_modal(CO_ERROR_NO_PROJECT),
            )
            return

        project = context["project"]
        proposed_so_far = await asyncio.to_thread(proposed_cost_total, project["id"])

        draft = await asyncio.to_thread(
            draft_change_order,
            brief_markdown=context["brief_markdown"],
            deliverables=context["deliverables"],
            trigger_text=change_order.get("trigger_text") or "",
            task_summary=change_order.get("task_description"),
            budget_total=project.get("budget_total"),
            currency=project.get("currency") or "INR",
            proposed_cost_so_far=proposed_so_far,
        )

        await client.views_update(
            view_id=view_id,
            hash=view_hash,
            view=build_change_order_modal(
                change_order_id=change_order_id,
                channel_id=channel_id,
                thread_ts=thread_ts,
                project_id=project_id,
                draft=draft,
            ),
        )
        logger.info("change_order_modal_opened change_order_id=%s", change_order_id)
    except Exception as exc:
        logger.exception("Failed to fill change order modal: %s", exc)
        try:
            await client.views_update(
                view_id=view_id,
                hash=view_hash,
                view=build_change_order_error_modal(
                    CO_ERROR_DRAFT_FAILED.format(detail=exc)
                ),
            )
        except Exception:
            logger.exception("Failed to update modal with error state")


async def _bootstrap_change_order_modal(
    client: AsyncWebClient,
    *,
    view_id: str,
    view_hash: str,
    channel_id: str,
    user_id: str,
    thread_ts: str,
    message_ts: str | None,
    message_text: str | None,
    source: str,
) -> None:
    lock_key = LockKeys.bootstrap(channel_id, user_id)
    if not try_acquire(lock_key):
        await client.views_update(
            view_id=view_id,
            hash=view_hash,
            view=build_change_order_error_modal(CO_ERROR_BOOTSTRAP_BUSY),
        )
        return

    try:
        context = await asyncio.to_thread(load_project_by_channel, channel_id)
        if not context:
            await client.views_update(
                view_id=view_id,
                hash=view_hash,
                view=build_change_order_error_modal(CO_ERROR_NO_PROJECT),
            )
            return

        project = context["project"]
        project_id = project["id"]
        if user_id != project.get("freelancer_slack_id"):
            await client.views_update(
                view_id=view_id,
                hash=view_hash,
                view=build_change_order_error_modal(CO_ERROR_FREELANCER_ONLY),
            )
            return

        if source == "shortcut":
            if not message_text:
                await client.views_update(
                    view_id=view_id,
                    hash=view_hash,
                    view=build_change_order_error_modal(CO_ERROR_NO_MESSAGE_TEXT),
                )
                return
            if message_ts and await asyncio.to_thread(
                flag_already_exists, project_id, message_ts
            ):
                await client.views_update(
                    view_id=view_id,
                    hash=view_hash,
                    view=build_change_order_error_modal(CO_ERROR_FLAG_EXISTS),
                )
                return
            trigger_text = message_text
        else:
            trigger_text = "Manual change order"

        change_order_id = await asyncio.to_thread(
            create_manual_scope_flag,
            project_id=project_id,
            trigger_text=trigger_text,
            message_ts=message_ts,
        )

        await _fill_change_order_modal(
            client,
            view_id=view_id,
            view_hash=view_hash,
            change_order_id=change_order_id,
            channel_id=channel_id,
            thread_ts=thread_ts or (message_ts or ""),
            project_id=project_id,
        )
        logger.info(
            "change_order_bootstrap_complete source=%s change_order_id=%s",
            source,
            change_order_id,
        )
    except Exception as exc:
        logger.exception("Failed to bootstrap change order modal: %s", exc)
        try:
            await client.views_update(
                view_id=view_id,
                hash=view_hash,
                view=build_change_order_error_modal(
                    CO_ERROR_PREPARE_FAILED.format(detail=exc)
                ),
            )
        except Exception:
            logger.exception("Failed to update bootstrap modal with error state")
    finally:
        release(lock_key)


async def open_change_order_bootstrap_modal(
    client: AsyncWebClient,
    *,
    trigger_id: str,
    ack,
    channel_id: str,
    user_id: str,
    thread_ts: str = "",
    message_ts: str | None = None,
    message_text: str | None = None,
    source: str,
) -> bool:
    """Open a loading modal before any DB/validation work (slash command / shortcut)."""
    if is_locked(LockKeys.bootstrap(channel_id, user_id)):
        await ack()
        return False

    open_resp = await open_view_with_trigger(
        client,
        trigger_id=trigger_id,
        view=build_bootstrap_loading_modal(
            channel_id=channel_id,
            user_id=user_id,
            thread_ts=thread_ts,
            message_ts=message_ts,
            message_text=message_text,
            source=source,
        ),
        ack=ack,
    )
    if not open_resp:
        return False

    view_id = open_resp["view"]["id"]
    view_hash = open_resp["view"]["hash"]
    asyncio.create_task(
        _bootstrap_change_order_modal(
            client,
            view_id=view_id,
            view_hash=view_hash,
            channel_id=channel_id,
            user_id=user_id,
            thread_ts=thread_ts,
            message_ts=message_ts,
            message_text=message_text,
            source=source,
        )
    )
    return True


async def open_change_order_modal(
    client: AsyncWebClient,
    *,
    trigger_id: str,
    ack,
    change_order_id: str,
    channel_id: str,
    thread_ts: str,
    project_id: str,
) -> bool:
    """Open loading modal immediately, then draft via AI in the background."""
    open_resp = await open_view_with_trigger(
        client,
        trigger_id=trigger_id,
        view=build_loading_change_order_modal(
            change_order_id=change_order_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            project_id=project_id,
        ),
        ack=ack,
    )
    if not open_resp:
        return False

    view_id = open_resp["view"]["id"]
    view_hash = open_resp["view"]["hash"]

    asyncio.create_task(
        _fill_change_order_modal(
            client,
            view_id=view_id,
            view_hash=view_hash,
            change_order_id=change_order_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            project_id=project_id,
        )
    )
    return True
