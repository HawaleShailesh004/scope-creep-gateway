from __future__ import annotations

from db.supabase_client import run_query
from services.canvas_model import build_canvas_markdown_from_project
from services.deliverables import (
    load_effective_deliverables,
    load_exclusions,
    load_in_scope_deliverables,
    sync_paid_change_orders_to_deliverables,
)


def load_project_by_channel(channel_id: str) -> dict | None:
    project_result = run_query(
        lambda sb: sb.table("projects")
        .select("*")
        .eq("slack_channel_id", channel_id)
        .limit(1)
    )
    if not project_result.data:
        return None

    project = project_result.data[0]
    sync_paid_change_orders_to_deliverables(project["id"])
    deliverable_rows = load_in_scope_deliverables(project["id"])
    deliverables = [row["description"] for row in deliverable_rows]
    exclusions = load_exclusions(project["id"])

    brief_markdown = build_canvas_markdown_from_project(project)

    return {
        "project": project,
        "deliverables": deliverables,
        "exclusions": exclusions,
        "deliverable_rows": deliverable_rows,
        "brief_markdown": brief_markdown,
    }
