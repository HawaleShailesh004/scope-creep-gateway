from services.mockup_classifier import is_mockup_work_request, pick_classifiable_file
from services.prefilter import should_skip_message


def test_file_share_with_mockup_and_request_passes():
    event = {
        "subtype": "file_share",
        "text": "here is the updated homepage mockup for review",
        "files": [{"filetype": "png", "url_private": "https://files.slack.com/x"}],
    }
    assert not should_skip_message(event)
    assert pick_classifiable_file(event) is not None


def test_file_share_without_request_context_skipped():
    event = {
        "subtype": "file_share",
        "text": "lol",
        "files": [{"filetype": "png"}],
    }
    assert should_skip_message(event)


def test_is_mockup_work_request_accepts_design_keyword():
    event = {"text": "see attached mockup", "files": []}
    assert is_mockup_work_request(event)
