"""Functions for API queries made when the bot starts."""
# All functions in this module are synchronous because they run once before the application start,
# so speed is irrelevant.
# Their being synchronous enables us to include them into BotData.__init__() without workarounds.
import logging
from typing import Any

import httpx

from samanthas_telegram_bot.api_clients.auxil.constants import (
    API_URL_INFIX_DAY_AND_TIME_SLOTS,
    API_URL_INFIX_ENROLLMENT_TESTS,
    API_URL_INFIX_LANGUAGES_AND_LEVELS,
    API_URL_PREFIX,
)
from samanthas_telegram_bot.data_structures.enums import AgeRangeType
from samanthas_telegram_bot.data_structures.models import (
    AgeRange,
    Assessment,
    AssessmentQuestion,
    AssessmentQuestionOption,
    DayAndTimeSlot,
    LanguageAndLevel,
)

logger = logging.getLogger(__name__)


def get_age_ranges() -> dict[AgeRangeType, tuple[AgeRange, ...]]:
    """Gets age ranges from the backend, assigns IDs (for bot phrases) to age ranges for teacher.

    Reasoning for assigning bot phrase IDs to age ranges: The bot asks the teacher about students'
    ages, adding words like "teenager" or "adult" to the number ranges (e.g. "children (5-11)",
    in user's language).

    These words have to be assigned to these age ranges for the bot to display the correct phrase.
    For example: `phrases.csv` contains the phrase with ID ``option_adults``, so the age range
    corresponding to adults has to be assigned ``bot_phrase_id: option_adults``.
    """

    data = _get_json(url_infix="age_ranges")

    age_ranges: dict[AgeRangeType, tuple[AgeRange, ...]] = {
        type_: tuple(AgeRange(**item) for item in data if item["type"] == type_)
        for type_ in (AgeRangeType.STUDENT, AgeRangeType.TEACHER)
    }

    # add IDs of bot phrases to teachers' age ranges
    age_to_phrase_id = {
        5: "young_children",
        9: "older_children",
        13: "adolescents",
        18: "adults",
        66: "seniors",
    }
    for age_range in age_ranges[AgeRangeType.TEACHER]:
        age_range.bot_phrase_id = f"option_{age_to_phrase_id[age_range.age_from]}"

    return age_ranges


def get_assessments(lang_code: str) -> dict[int, Assessment]:
    """Gets assessment questions from the backend, based on language.

    Returns a dictionary matching an age range ID to assessment.
    """

    data = _get_json(
        url_infix=API_URL_INFIX_ENROLLMENT_TESTS,
        name_for_logger=f"assessments for {lang_code=}",
        params={"language": lang_code},
    )

    assessments = tuple(
        Assessment(
            id=item["id"],
            age_range_ids=tuple(item["age_ranges"]),
            questions=tuple(
                AssessmentQuestion(
                    id=question["id"],
                    text=question["text"],
                    options=tuple(
                        AssessmentQuestionOption(**option) for option in question["options"]
                    ),
                )
                for question in item["questions"]
            ),
        )
        for item in data
    )

    # Each assessment has a sequence of age range IDs. We have to match every single age range ID
    # in this sequence to a respective assessment.
    assessment_for_age_range_id = {
        age_range_id: assessment
        for assessment in assessments
        for age_range_id in assessment.age_range_ids
    }

    return assessment_for_age_range_id


def get_day_and_time_slots() -> tuple[DayAndTimeSlot, ...]:
    """Gets day and time slots from the backend."""

    def get_hour(str_: str) -> int:
        """Takes a string like 05:00:00 and returns hours (5 in this example)."""
        return int(str_.split(":")[0])

    data = _get_json(url_infix=API_URL_INFIX_DAY_AND_TIME_SLOTS)

    return tuple(
        DayAndTimeSlot(
            id=item["id"],
            day_of_week_index=item["day_of_week_index"],
            from_utc_hour=get_hour(item["time_slot"]["from_utc_hour"]),
            to_utc_hour=get_hour(item["time_slot"]["to_utc_hour"]),
        )
        for item in data
    )


def get_languages_and_levels() -> tuple[LanguageAndLevel, ...]:
    """Gets languages and levels from the backend."""

    data = _get_json(
        url_infix=API_URL_INFIX_LANGUAGES_AND_LEVELS,
        name_for_logger="combinations of languages and levels",
    )

    return tuple(
        LanguageAndLevel(id=item["id"], language_id=item["language"]["id"], level=item["level"])
        for item in data
    )


def _get_json(
    url_infix: str,
    name_for_logger: str | None = None,
    params: dict[str, str] | None = None,
) -> Any:
    """Function for simple synchronous GET requests with logging."""
    if not name_for_logger:
        name_for_logger = url_infix.replace("_", " ")

    logger.info(f"Getting {name_for_logger} from the backend...")

    # synchronous requests are only run at application startup, so no exception handling needed
    response = httpx.get(f"{API_URL_PREFIX}/{url_infix}/", params=params)

    data = response.json()
    logger.info(f"...received {len(data)} {name_for_logger}.")

    return data
