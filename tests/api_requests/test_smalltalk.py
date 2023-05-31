import json

import pytest

import samanthas_telegram_bot.api_queries.smalltalk as smalltalk
from samanthas_telegram_bot.data_structures.enums import SmalltalkTestStatus
from tests.constants import TEST_DIR

API_TEST_DIR = TEST_DIR / "api_requests"
SMALLTALK_TEST_DIR = API_TEST_DIR / "smalltalk_json"


@pytest.mark.parametrize(
    "file_stem, expected_level",
    [
        ("status_completed_score_b2", "B2"),
        ("status_completed_score_b2p", "B2"),
        ("status_completed_score_c1", "C1"),
        ("status_completed_score_undefined", None),
    ],
)
def test_process_smalltalk_json_status_complete_with_valid_level(file_stem, expected_level):
    file = SMALLTALK_TEST_DIR / f"{file_stem}.json"
    text = file.read_text()
    result = smalltalk.process_smalltalk_json(text)
    assert result.status == SmalltalkTestStatus.RESULTS_READY
    assert result.level == expected_level
    assert result.url.startswith("http")
    assert result.json == json.loads(text)


@pytest.mark.parametrize(
    "file_stem, expected_status",
    [
        ("status_processing", SmalltalkTestStatus.RESULTS_NOT_READY),
        (
            "status_sent_(interview_not_started_or_in_progress)",
            SmalltalkTestStatus.NOT_STARTED_OR_IN_PROGRESS,
        ),
    ],
)
def test_process_smalltalk_json_status_processing_or_sent(file_stem, expected_status):
    file = SMALLTALK_TEST_DIR / f"{file_stem}.json"
    result = smalltalk.process_smalltalk_json(file.read_text())
    assert result.status == expected_status
    assert not any(getattr(result, attr) for attr in ("level", "url", "json"))
