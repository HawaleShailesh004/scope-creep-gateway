from __future__ import annotations

from typing import Any

from services.billing_status import billing_summary
from services.brief_template import format_budget
from services.capacity import absorbed_hours, top_absorbed_client_label
from services.clients import client_stats, get_client
from services.capacity import absorbed_hours_by_client
from db.supabase_client import get_supabase
from services.user_messages import STUDIO_WEEKLY_SUMMARY, WEEKLY_BILLING_LINE


def _project_health_emoji(scope_health: int | None) -> str:
    health = scope_health if scope_health is not None else 100
    if health >= 85:
        return "🟢"
    if health >= 60:
        return "🟡"
    return "🔴"


def _heaviest_creeper_label(freelancer_slack_id: str) -> str | None:
    supabase = get_supabase()
    projects = (
        supabase.table("projects")
        .select("id, client_slack_id, project_name")
        .eq("freelancer_slack_id", freelancer_slack_id)
        .execute()
        .data
        or []
    )
    if not projects:
        return None

    best_label = None
    best_asks = -1
    for project in projects:
        client_slack_id = project.get("client_slack_id")
        if not client_slack_id:
            continue
        client_uuid = _resolve_client_id(freelancer_slack_id, client_slack_id)
        if not client_uuid:
            continue
        stats = client_stats(client_uuid)
        asks = stats.get("monthly_asks", 0)
        if asks > best_asks:
            best_asks = asks
            best_label = stats.get("client_label") or project.get("project_name")
    return best_label if best_asks > 0 else None


def _resolve_client_id(freelancer_slack_id: str, client_slack_id: str) -> str | None:
    from services.clients import resolve_client

    try:
        return resolve_client(
            freelancer_slack_id=freelancer_slack_id,
            client_slack_id=client_slack_id,
        )
    except Exception:
        return None


def _cleanest_project_label(freelancer_slack_id: str) -> str | None:
    supabase = get_supabase()
    rows = (
        supabase.table("projects")
        .select("project_name, scope_health")
        .eq("freelancer_slack_id", freelancer_slack_id)
        .order("scope_health", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return None
    row = rows[0]
    if (row.get("scope_health") or 100) >= 95:
        return row.get("project_name")
    return None


def build_studio_weekly_summary(
    freelancer_slack_id: str,
    *,
    studio_name: str = "Keystone Digital Studio",
    currency: str = "INR",
) -> str:
    supabase = get_supabase()
    projects = (
        supabase.table("projects")
        .select("id, project_name, scope_health")
        .eq("freelancer_slack_id", freelancer_slack_id)
        .execute()
        .data
        or []
    )
    active_count = len(projects)

    cap = absorbed_hours(freelancer_slack_id, period="week")
    billing = billing_summary(freelancer_slack_id, period="week")
    top_client = top_absorbed_client_label(freelancer_slack_id, period="week")
    heaviest = _heaviest_creeper_label(freelancer_slack_id)
    cleanest = _cleanest_project_label(freelancer_slack_id)

    breakdown = absorbed_hours_by_client(freelancer_slack_id, period="week")
    if breakdown and not top_client:
        top_client = "a client"

    lumen_note = ""
    if heaviest:
        lumen_note = f"🚩 {heaviest} is your heaviest creeper this month."
    clean_note = ""
    if cleanest:
        clean_note = f"🟢 {cleanest} is clean - right on scope."

    worth_note = ""
    if cap["hours"] >= 6 and top_client:
        worth_note = (
            f"Worth a look: absorbed hours are climbing - heaviest so far is {top_client}."
        )

    billing_line = WEEKLY_BILLING_LINE.format(
        billed=format_budget(billing["billed"], currency),
        approved=format_budget(billing["approved"], currency),
        pending=format_budget(billing["pending"], currency),
    )

    return STUDIO_WEEKLY_SUMMARY.format(
        studio_name=studio_name,
        active_projects=active_count,
        absorbed_hours=cap["hours"],
        absorbed_value=format_budget(cap["value"], currency),
        client_count=max(cap["client_count"], 1),
        top_client=top_client or "-",
        billing_line=billing_line,
        heaviest_line=lumen_note,
        clean_line=clean_note,
        worth_line=worth_note,
    )
