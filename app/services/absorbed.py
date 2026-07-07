from __future__ import annotations

from typing import Any

from db.supabase_client import get_supabase

ABSORB_VALUE_THRESHOLD = 3000
ABSORB_COUNT_THRESHOLD = 3


def log_absorbed(
    *,
    project_id: str,
    client_id: str | None,
    trigger_message_ts: str | None,
    trigger_text: str | None,
    task_summary: str | None,
    estimated_value: float | None,
    estimated_hours: float | None = None,
    size: str | None,
    source: str = "manual",
) -> str:
    supabase = get_supabase()
    row = {
        "project_id": project_id,
        "client_id": client_id,
        "trigger_message_ts": trigger_message_ts,
        "trigger_text": trigger_text,
        "task_summary": task_summary,
        "estimated_value": estimated_value,
        "estimated_hours": estimated_hours,
        "size": size,
        "source": source,
    }
    result = supabase.table("absorbed_items").insert(row).execute()
    return result.data[0]["id"]


def running_total(
    *,
    project_id: str | None = None,
    client_id: str | None = None,
) -> dict[str, Any]:
    if not project_id and not client_id:
        return {"count": 0, "total_value": 0.0, "manual_count": 0, "auto_count": 0}

    supabase = get_supabase()
    query = supabase.table("absorbed_items").select(
        "estimated_value, estimated_hours, source, created_at"
    )
    if client_id:
        query = query.eq("client_id", client_id)
    elif project_id:
        query = query.eq("project_id", project_id)
    else:
        return {"count": 0, "total_value": 0.0, "manual_count": 0, "auto_count": 0}

    rows = query.execute().data or []
    total_value = sum(float(r.get("estimated_value") or 0) for r in rows)
    total_hours = sum(float(r.get("estimated_hours") or 0) for r in rows)
    manual = sum(1 for r in rows if r.get("source") == "manual")
    auto = sum(1 for r in rows if r.get("source") == "auto")
    return {
        "count": len(rows),
        "total_value": total_value,
        "total_hours": round(total_hours, 1),
        "manual_count": manual,
        "auto_count": auto,
    }


def threshold_crossed(totals: dict[str, Any]) -> bool:
    return (
        totals.get("count", 0) >= ABSORB_COUNT_THRESHOLD
        or totals.get("total_value", 0) >= ABSORB_VALUE_THRESHOLD
    )


def format_absorbed_total(totals: dict[str, Any], currency: str = "INR") -> str:
    value = totals.get("total_value", 0)
    symbol = "₹" if currency == "INR" else f"{currency} "
    return f"{symbol}{value:,.0f}"
