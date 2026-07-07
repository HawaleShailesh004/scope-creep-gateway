from __future__ import annotations

import logging
from typing import Literal

from services.scope_canvas import CanvasModel, build_full_canvas_markdown
from services.slack_canvas import replace_canvas_markdown

logger = logging.getLogger(__name__)

UpdateMode = Literal["full", "incremental"]


async def push_canvas_update(
    user_token: str,
    *,
    canvas_id: str,
    model: CanvasModel,
    mode: UpdateMode = "full",
    title: str | None = None,
) -> bool:
    """
    Update a canvas with a full document replace.

    Incremental section edits are disabled: Slack's canvases.edit replace on a
    single section_id does not remove sibling sections when the replacement
    markdown contains multiple headings, which caused duplicated blocks in live
    testing. Full rebuild is fast enough at our volume and is always correct.
    """
    if mode == "incremental":
        logger.info(
            "canvas incremental requested for %s — using full rebuild (section "
            "replace duplicates content with multi-heading markdown)",
            canvas_id,
        )

    await replace_canvas_markdown(
        user_token,
        canvas_id=canvas_id,
        content=build_full_canvas_markdown(model),
        title=title,
    )
    return True
