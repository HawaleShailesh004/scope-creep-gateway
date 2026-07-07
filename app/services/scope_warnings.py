from __future__ import annotations



import asyncio

import json

import logging

import os

from typing import Any



from slack_sdk.web.async_client import AsyncWebClient



from db.supabase_client import get_supabase

from listeners.views.warning_card import build_warning_blocks

from services.absorbed import (

    format_absorbed_total,

    running_total,

    threshold_crossed,

)

from services.clients import monthly_ask_count

from services.capacity import capacity_nudge

from services.rts_search import search_prior_mention

from services.user_messages import (

    ABSORB_THRESHOLD_NUDGE,

    CAPACITY_NUDGE,

    CLIENT_PATTERN_NUDGE,

    SCOPE_WARNING_TITLE,

)



logger = logging.getLogger(__name__)





def flag_already_exists(project_id: str, message_ts: str) -> bool:

    supabase = get_supabase()

    existing = (

        supabase.table("change_orders")

        .select("id")

        .eq("project_id", project_id)

        .eq("trigger_message_ts", message_ts)

        .limit(1)

        .execute()

    )

    return bool(existing.data)





def create_scope_flag(

    *,

    project_id: str,

    message_ts: str,

    message_text: str,

    classification: dict[str, Any],

    prior_mention_found: bool,

    client_id: str | None = None,

) -> str:

    supabase = get_supabase()

    row = {

        "project_id": project_id,

        "client_id": client_id,

        "trigger_message_ts": message_ts,

        "trigger_text": message_text,

        "task_description": classification.get("new_task_summary"),

        "confidence": classification.get("confidence"),

        "prior_mention_found": prior_mention_found,

        "size": classification.get("size"),

        "estimated_value": classification.get("estimated_value"),

        "estimated_hours": classification.get("estimated_hours"),

        "status": "flagged",

        "origin": "flag",

    }

    result = supabase.table("change_orders").insert(row).execute()

    return result.data[0]["id"]





def create_manual_scope_flag(

    *,

    project_id: str,

    trigger_text: str,

    message_ts: str | None = None,

    client_id: str | None = None,

) -> str:

    supabase = get_supabase()

    row = {

        "project_id": project_id,

        "client_id": client_id,

        "trigger_message_ts": message_ts,

        "trigger_text": trigger_text,

        "status": "flagged",

        "prior_mention_found": False,

        "origin": "manual",

    }

    result = supabase.table("change_orders").insert(row).execute()

    return result.data[0]["id"]





def dismiss_scope_flag(change_order_id: str) -> None:

    supabase = get_supabase()

    supabase.table("change_orders").update({"status": "dismissed"}).eq(

        "id", change_order_id

    ).execute()





def _lookup_prior_mention(

    *,

    channel_id: str,

    search_query: str,

    message_ts: str,

    disclosure_ts: str | None,

) -> tuple[bool, str | None]:

    user_token = os.environ.get("SLACK_USER_TOKEN")

    if not user_token:

        logger.debug("RTS skip: SLACK_USER_TOKEN not set")

        return False, None



    return search_prior_mention(

        user_token,

        channel_id=channel_id,

        query=search_query,

        before_ts=message_ts,

        exclude_ts=message_ts,

        after_ts=disclosure_ts,

    )





def _build_nudges(

    *,

    project: dict[str, Any],

    client_id: str | None,

    additional_hours: float = 0.0,

) -> tuple[str | None, str | None, str | None]:

    absorb_nudge = None

    client_pattern_nudge = None

    capacity_nudge_text = None

    currency = project.get("currency") or "INR"



    totals = running_total(

        project_id=project["id"],

        client_id=client_id,

    )

    if threshold_crossed(totals):

        absorb_nudge = ABSORB_THRESHOLD_NUDGE.format(

            total=format_absorbed_total(totals, currency)

        )



    if client_id:

        nth = monthly_ask_count(client_id)

        if nth >= 2:

            from services.clients import get_client



            client = get_client(client_id)

            label = (client or {}).get("client_label") or "this client"

            client_pattern_nudge = CLIENT_PATTERN_NUDGE.format(

                nth=_ordinal(nth), client=label

            )



    hours = capacity_nudge(

        project.get("freelancer_slack_id") or "",

        additional_hours=additional_hours,

    )

    if hours:

        capacity_nudge_text = CAPACITY_NUDGE.format(hours=hours)



    return absorb_nudge, client_pattern_nudge, capacity_nudge_text





def _ordinal(n: int) -> str:

    if 10 <= n % 100 <= 20:

        suffix = "th"

    else:

        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

    return f"{n}{suffix}"





async def send_scope_warning(

    client: AsyncWebClient,

    *,

    channel_id: str,

    freelancer_id: str,

    message_ts: str,

    message_text: str,

    project: dict[str, Any],

    classification: dict[str, Any],

    client_id: str | None = None,

    revision_deliverable: str | None = None,

    revision_limit: int | None = None,

) -> None:

    project_id = project["id"]



    if await asyncio.to_thread(flag_already_exists, project_id, message_ts):

        logger.debug("scope_warning_skip already_warned ts=%s", message_ts)

        return



    search_query = (

        classification.get("new_task_summary") or message_text

    ).strip()

    prior_found, prior_date = await asyncio.to_thread(

        _lookup_prior_mention,

        channel_id=channel_id,

        search_query=search_query,

        message_ts=message_ts,

        disclosure_ts=project.get("disclosure_ts"),

    )



    change_order_id = await asyncio.to_thread(

        create_scope_flag,

        project_id=project_id,

        message_ts=message_ts,

        message_text=message_text,

        classification=classification,

        prior_mention_found=prior_found,

        client_id=client_id,

    )



    absorb_nudge, client_pattern_nudge, capacity_nudge_text = _build_nudges(

        project=project,

        client_id=client_id,

        additional_hours=float(classification.get("estimated_hours") or 0),

    )



    blocks = build_warning_blocks(

        client_message=message_text,

        new_task_summary=classification.get("new_task_summary"),

        prior_mention_date=prior_date if prior_found else None,

        change_order_id=change_order_id,

        channel_id=channel_id,

        message_ts=message_ts,

        project_id=project_id,

        absorb_nudge=absorb_nudge,

        client_pattern_nudge=client_pattern_nudge,

        capacity_nudge=capacity_nudge_text,

        revision_deliverable=revision_deliverable,

        revision_limit=revision_limit,

    )



    await client.chat_postEphemeral(
        channel=channel_id,
        user=freelancer_id,
        text=SCOPE_WARNING_TITLE,
        blocks=blocks,
    )



    logger.info(

        "scope_warning_sent %s",

        json.dumps(

            {

                "channel_id": channel_id,

                "freelancer_id": freelancer_id,

                "message_ts": message_ts,

                "change_order_id": change_order_id,

                "prior_mention_found": prior_found,

            },

            ensure_ascii=False,

        ),

    )

