import pytest

from services.slack_mcp import SlackMcpError, _extract_canvas_id


def test_extract_canvas_id_from_json_text():
    result = {
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": (
                        '{"canvas_id":"F0BEQ2M08JZ",'
                        '"canvas_url":"https://example.com/docs/F0BEQ2M08JZ"}'
                    ),
                }
            ]
        }
    }
    assert _extract_canvas_id(result) == "F0BEQ2M08JZ"


def test_extract_canvas_id_rejects_literal_canvas_id_string():
    result = {
        "result": {
            "content": [{"type": "text", "text": "canvas_id"}],
        }
    }
    with pytest.raises(SlackMcpError):
        _extract_canvas_id(result)


def test_extract_canvas_id_from_structured_content():
    result = {
        "result": {
            "structuredContent": {"canvas_id": "F0BEM541ZEF"},
        }
    }
    assert _extract_canvas_id(result) == "F0BEM541ZEF"
