from services.message_text import extract_message_text, meaningful_word_count

# Subtypes we never classify (edits, deletes, joins, etc.)
_SKIP_SUBTYPES = frozenset(
    {
        "message_changed",
        "message_deleted",
        "channel_join",
        "channel_leave",
        "channel_topic",
        "channel_purpose",
        "channel_name",
        "channel_archive",
        "channel_unarchive",
        "group_join",
        "group_leave",
        "thread_broadcast",
        "bot_message",
    }
)


def should_skip_message(event: dict) -> bool:
    subtype = event.get("subtype")

    if subtype == "file_share":
        from services.mockup_classifier import (
            is_mockup_work_request,
            pick_classifiable_file,
        )

        if pick_classifiable_file(event) and is_mockup_work_request(event):
            return False
        return True

    if subtype:
        if subtype in _SKIP_SUBTYPES:
            return True
        return True

    if event.get("bot_id"):
        return True

    text = extract_message_text(event)
    if not text:
        return True

    if meaningful_word_count(text) < 3:
        return True

    return False


def is_project_channel_message(event: dict) -> bool:
    channel_type = event.get("channel_type")
    if channel_type == "im":
        return False
    if channel_type in ("channel", "group"):
        return True

    channel_id = event.get("channel", "")
    return channel_id.startswith(("C", "G"))
