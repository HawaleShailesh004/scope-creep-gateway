from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from db.supabase_client import get_supabase


def resolve_client(
    *,
    freelancer_slack_id: str,
    client_slack_id: str,
    client_label: str | None = None,
) -> str:
    supabase = get_supabase()
    existing = (
        supabase.table("clients")
        .select("id")
        .eq("freelancer_slack_id", freelancer_slack_id)
        .eq("client_slack_id", client_slack_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        client_id = existing.data[0]["id"]
        if client_label:
            supabase.table("clients").update({"client_label": client_label}).eq(
                "id", client_id
            ).execute()
        return client_id

    row = {
        "freelancer_slack_id": freelancer_slack_id,
        "client_slack_id": client_slack_id,
        "client_label": client_label,
    }
    result = supabase.table("clients").insert(row).execute()
    return result.data[0]["id"]


def get_client(client_id: str) -> dict | None:
    supabase = get_supabase()
    result = (
        supabase.table("clients")
        .select("*")
        .eq("id", client_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def client_stats(client_id: str) -> dict[str, Any]:
    supabase = get_supabase()
    client = get_client(client_id)
    if not client:
        return {}

    projects = (
        supabase.table("projects")
        .select("id")
        .eq("freelancer_slack_id", client["freelancer_slack_id"])
        .eq("client_slack_id", client["client_slack_id"])
        .execute()
        .data
        or []
    )
    project_ids = [p["id"] for p in projects]

    flags = 0
    absorbed_count = 0
    absorbed_value = 0.0
    absorbed_hours = 0.0
    billed_count = 0
    monthly_asks = 0
    approved_value = 0.0
    pending_value = 0.0

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if project_ids:
        co_rows = (
            supabase.table("change_orders")
            .select("status, estimated_value, created_at, origin")
            .in_("project_id", project_ids)
            .execute()
            .data
            or []
        )
        for row in co_rows:
            if row.get("status") == "flagged":
                flags += 1
                created = row.get("created_at", "")
                if created and created >= month_start.isoformat():
                    monthly_asks += 1
            if row.get("status") == "paid":
                billed_count += 1
                approved_value += float(row.get("estimated_cost") or row.get("estimated_value") or 0)
            if row.get("status") == "proposed":
                pending_value += float(row.get("estimated_cost") or row.get("estimated_value") or 0)

        absorbed_rows = (
            supabase.table("absorbed_items")
            .select("estimated_value, estimated_hours, created_at")
            .in_("project_id", project_ids)
            .execute()
            .data
            or []
        )
        for row in absorbed_rows:
            absorbed_count += 1
            absorbed_value += float(row.get("estimated_value") or 0)
            absorbed_hours += float(row.get("estimated_hours") or 0)
            created = row.get("created_at", "")
            if created and created >= month_start.isoformat():
                monthly_asks += 1

    label = client.get("client_label") or f"<@{client['client_slack_id']}>"
    return {
        "client_id": client_id,
        "client_label": label,
        "project_count": len(project_ids),
        "open_flags": flags,
        "absorbed_count": absorbed_count,
        "absorbed_value": absorbed_value,
        "absorbed_hours": round(absorbed_hours, 1),
        "billed_count": billed_count,
        "approved_value": approved_value,
        "pending_value": pending_value,
        "monthly_asks": monthly_asks,
    }


def monthly_ask_count(client_id: str) -> int:
    return client_stats(client_id).get("monthly_asks", 0)
