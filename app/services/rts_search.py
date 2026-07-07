from __future__ import annotations



import logging

from datetime import datetime, timezone



import httpx



logger = logging.getLogger(__name__)



SLACK_API_URL = "https://slack.com/api/assistant.search.context"





def _format_message_date(message_ts: str) -> str:

    ts = float(message_ts)

    dt = datetime.fromtimestamp(ts, tz=timezone.utc)

    return dt.strftime("%b %d, %Y")





def search_prior_mention(

    user_token: str,

    *,

    channel_id: str,

    query: str,

    before_ts: str,

    exclude_ts: str | None = None,

    after_ts: str | None = None,

) -> tuple[bool, str | None]:

    """Search channel history for an earlier mention of the same request.



    Returns (prior_mention_found, human-readable date of earliest match).

    Messages before disclosure_ts (after_ts) are excluded.

    """

    if not query.strip():

        return False, None



    before = int(float(before_ts))

    payload: dict = {

        "query": query,

        "context_channel_id": channel_id,

        "content_types": ["messages"],

        "channel_types": ["public_channel", "private_channel"],

        "before": before,

        "limit": 10,

        "disable_semantic_search": True,

        "include_bots": False,

        "sort": "timestamp",

        "sort_dir": "desc",

    }

    if after_ts:

        payload["after"] = int(float(after_ts))



    try:

        resp = httpx.post(

            SLACK_API_URL,

            headers={"Authorization": f"Bearer {user_token}"},

            json=payload,

            timeout=15.0,

        )

        data = resp.json()

    except httpx.HTTPError as exc:

        logger.warning("RTS search request failed: %s", exc)

        return False, None



    if not data.get("ok"):

        logger.warning("RTS search API error: %s", data.get("error"))

        return False, None



    messages = data.get("results", {}).get("messages", [])

    prior_matches = []

    disclosure_floor = float(after_ts) if after_ts else None

    for msg in messages:

        msg_ts = str(msg.get("message_ts", ""))

        if not msg_ts:

            continue

        if exclude_ts and msg_ts == exclude_ts:

            continue

        if msg.get("channel_id") and msg["channel_id"] != channel_id:

            continue

        if disclosure_floor is not None and float(msg_ts) < disclosure_floor:

            continue

        prior_matches.append(msg_ts)



    if not prior_matches:

        return False, None



    earliest_ts = min(prior_matches, key=float)

    return True, _format_message_date(earliest_ts)

