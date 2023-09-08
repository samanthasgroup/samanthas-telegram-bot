from typing import Any

from samanthas_telegram_bot.api_clients.auxil.constants import (
    API_URL_AGE_RANGES,
    API_URL_DAY_AND_TIME_SLOTS,
    API_URL_ENROLLMENT_TESTS,
    API_URL_LANGUAGES_AND_LEVELS,
)
from samanthas_telegram_bot.api_clients.base.base_api_client import BaseApiClient


class BackendClientWithoutUpdateAndContext(BaseApiClient):
    """A simplified backend client that requires no ``Update`` or ``Context`` objects.

    Makes synchronous requests.
    """

    @classmethod
    def get_age_ranges(cls) -> Any:
        return cls.get_simple(API_URL_AGE_RANGES)

    @classmethod
    def get_assessments(cls, lang_code: str) -> Any:
        return cls.get_simple(API_URL_ENROLLMENT_TESTS, params={"language": lang_code})

    @classmethod
    def get_day_and_time_slots(cls) -> Any:
        return cls.get_simple(API_URL_DAY_AND_TIME_SLOTS)

    @classmethod
    def get_languages_and_levels(cls) -> Any:
        return cls.get_simple(API_URL_LANGUAGES_AND_LEVELS)
