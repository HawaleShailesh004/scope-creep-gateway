from __future__ import annotations

import asyncio
import logging
import os
from typing import Literal

from services.canvas_model import build_canvas_model
from services.canvas_resolver import ensure_project_canvas_id
from services.canvas_updater import push_canvas_update
from services.change_orders import (
    compute_project_scope_health,
    list_absorbed_items,
    list_project_change_orders,
    save_project_scope_health,
)
from services.embedding_cache import refresh_embedding_refs
from services.operation_locks import LockKeys, operation_lock
from services.project_context import load_project_by_channel
from services.slack_canvas import SlackCanvasError

logger = logging.getLogger(__name__)

UpdateMode = Literal["full", "incremental"]


async def refresh_project_canvas(
    channel_id: str,
    project_id: str,
    *,
    mode: UpdateMode = "full",
) -> tuple[int, bool]:
    """
    Recompute scope health, persist to DB, and refresh the channel canvas.

    Uses per-project lock + full document replace (reliable; no section dupes).
    """
    context = await asyncio.to_thread(load_project_by_channel, channel_id)
    if not context:
        raise RuntimeError(f"No project for channel {channel_id}")

    project = context["project"]
    deliverable_rows = context["deliverable_rows"]
    change_orders = await asyncio.to_thread(list_project_change_orders, project_id)
    absorbed = await asyncio.to_thread(list_absorbed_items, project_id)
    health = await asyncio.to_thread(
        compute_project_scope_health, project, change_orders, absorbed
    )
    scope_health = health.committed

    await asyncio.to_thread(save_project_scope_health, project_id, scope_health)
    await asyncio.to_thread(
        refresh_embedding_refs, project_id, context["deliverables"]
    )

    model = build_canvas_model(
        project,
        deliverable_rows=deliverable_rows,
        change_orders=change_orders,
        health=health,
    )

    user_token = os.environ.get("SLACK_USER_TOKEN")
    if not user_token:
        logger.warning("Skipping canvas update — SLACK_USER_TOKEN is not set")
        return scope_health, False

    canvas_id = await ensure_project_canvas_id(
        project_id=project_id,
        channel_id=channel_id,
        stored_canvas_id=project.get("canvas_id"),
        user_token=user_token,
        project_name=project["project_name"],
    )
    if not canvas_id:
        logger.warning(
            "Skipping canvas update — could not resolve canvas id for channel %s",
            channel_id,
        )
        return scope_health, False

    title = f"Project Brief — {project['project_name']}"

    async with operation_lock(LockKeys.canvas(project_id)) as acquired:
        if not acquired:
            logger.warning(
                "Canvas update skipped — lock held for project %s", project_id
            )
            return scope_health, False

        try:
            await push_canvas_update(
                user_token,
                canvas_id=canvas_id,
                model=model,
                mode=mode,
                title=title,
            )
            return scope_health, True
        except SlackCanvasError as exc:
            logger.warning("Canvas update failed: %s", exc)
            return scope_health, False
