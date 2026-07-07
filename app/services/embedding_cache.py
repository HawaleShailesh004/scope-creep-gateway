from __future__ import annotations

import logging
from typing import Optional

from db.supabase_client import get_supabase
from services.embedding_gate import ReferenceVectors, build_reference_vectors

logger = logging.getLogger(__name__)

_refs_by_project: dict[str, ReferenceVectors] = {}


def _known_creep_texts(project_id: str) -> list[str]:
    """Past out-of-scope asks for sharper Stage-2 margin (optional)."""
    supabase = get_supabase()
    texts: list[str] = []
    orders = (
        supabase.table("change_orders")
        .select("task_description, trigger_text")
        .eq("project_id", project_id)
        .in_("status", ["flagged", "proposed", "paid"])
        .execute()
        .data
        or []
    )
    for row in orders:
        for key in ("task_description", "trigger_text"):
            value = (row.get(key) or "").strip()
            if value and value not in texts:
                texts.append(value[:300])

    absorbed = (
        supabase.table("absorbed_items")
        .select("task_summary, trigger_text")
        .eq("project_id", project_id)
        .execute()
        .data
        or []
    )
    for row in absorbed:
        for key in ("task_summary", "trigger_text"):
            value = (row.get(key) or "").strip()
            if value and value not in texts:
                texts.append(value[:300])
    return texts[:40]


def refresh_embedding_refs(
    project_id: str,
    deliverable_texts: list[str],
) -> ReferenceVectors:
    creep = _known_creep_texts(project_id)
    refs = build_reference_vectors(deliverable_texts, creep or None)
    _refs_by_project[project_id] = refs
    if refs.ready:
        logger.debug(
            "embedding_refs_refreshed project_id=%s deliverables=%s creep_refs=%s",
            project_id,
            len(deliverable_texts),
            len(creep),
        )
    return refs


def get_embedding_refs(project_id: str) -> Optional[ReferenceVectors]:
    return _refs_by_project.get(project_id)


def ensure_embedding_refs(
    project_id: str,
    deliverable_texts: list[str],
) -> ReferenceVectors:
    existing = _refs_by_project.get(project_id)
    if existing and existing.ready:
        return existing
    return refresh_embedding_refs(project_id, deliverable_texts)
