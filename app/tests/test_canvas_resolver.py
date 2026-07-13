from services.canvas_resolver import _parse_canvas_ids_from_search


def test_parse_canvas_ids_from_search():
    text = """
### Result 1 of 2
Title: Scope Health - Project redesign
File ID: F0BEV38ME4C
### Result 2 of 2
File ID: F0BEJQKFECB
"""
    assert _parse_canvas_ids_from_search(text) == ["F0BEV38ME4C", "F0BEJQKFECB"]
