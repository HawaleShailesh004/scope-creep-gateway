from services.message_text import (
    extract_message_text,
    meaningful_word_count,
    truncate_for_classifier,
    truncate_for_display,
)
from services.prefilter import should_skip_message


def test_extract_message_text_from_plain_text():
    assert extract_message_text({"text": "  hello   world  "}) == "hello world"


def test_extract_message_text_from_blocks():
    event = {
        "blocks": [
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [{"type": "text", "text": "can you add a blog"}],
                    }
                ],
            }
        ]
    }
    assert extract_message_text(event) == "can you add a blog"


def test_meaningful_word_count_ignores_urls():
    assert meaningful_word_count("check https://example.com please now") == 3
    assert meaningful_word_count("https://example.com https://other.com") == 0


def test_truncate_for_classifier_long_message():
    long_text = "word " * 2000
    result = truncate_for_classifier(long_text, max_chars=100)
    assert "truncated" in result
    assert result.startswith("word")


def test_truncate_for_display():
    assert truncate_for_display("short") == "short"
    assert truncate_for_display("x" * 300).endswith("...")


def test_should_skip_link_only_style_messages():
    assert should_skip_message({"text": "https://example.com https://other.com ok"})
