import samanthas_telegram_bot.api_queries.smalltalk as smalltalk
from samanthas_telegram_bot.data_structures.constants import ALL_LEVELS
from samanthas_telegram_bot.data_structures.enums import SmalltalkTestStatus
from tests.constants import TEST_DIR

API_TEST_DIR = TEST_DIR / "api_requests"


DATA_FILES = tuple((API_TEST_DIR / "smalltalk_json").glob("*.json"))


def test_process_smalltalk_json():
    for file in DATA_FILES:
        result = smalltalk.process_smalltalk_json(file.read_text())

        if "completed" in file.stem or "undefined" in file.stem:
            assert result.status == SmalltalkTestStatus.RESULTS_READY
            assert all(getattr(result, attr) for attr in ("level", "url", "full_json"))
            assert result.level in ALL_LEVELS
        elif "processing" in file.stem:
            assert result.status == SmalltalkTestStatus.RESULTS_NOT_READY
            assert not any(getattr(result, attr) for attr in ("level", "url", "full_json"))
        else:
            assert result.status == SmalltalkTestStatus.NOT_STARTED_OR_IN_PROGRESS
            assert not any(getattr(result, attr) for attr in ("level", "url", "full_json"))

        if "undefined" in file.stem:
            assert result.level == "A0"
