from __future__ import annotations

from decimal import Decimal

from db.supabase_client import get_supabase
from services.brief_template import parse_deliverables


def load_setup_deliverables(project_id: str) -> list[dict]:
    supabase = get_supabase()
    result = (
        supabase.table("deliverables")
        .select("*")
        .eq("project_id", project_id)
        .eq("origin", "setup")
        .execute()
    )
    return result.data or []


def update_project_brief(
    *,
    project_id: str,
    project_name: str,
    deliverables: list[str],
    budget_total: Decimal | None,
    deadline: str | None,
    default_revision_limit: int | None = None,
) -> None:
    """Update setup deliverables; preserve change_order origin rows."""
    supabase = get_supabase()

    supabase.table("projects").update(
        {
            "project_name": project_name,
            "budget_total": float(budget_total) if budget_total is not None else None,
            "deadline": deadline,
        }
    ).eq("id", project_id).execute()

    supabase.table("deliverables").delete().eq("project_id", project_id).eq(
        "origin", "setup"
    ).execute()

    rows = [
        {
            "project_id": project_id,
            "description": item,
            "origin": "setup",
            "revision_limit": default_revision_limit,
        }
        for item in deliverables
    ]
    if rows:
        supabase.table("deliverables").insert(rows).execute()
