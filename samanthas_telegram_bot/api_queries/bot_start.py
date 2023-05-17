"""Functions for API queries made when the bot starts."""
# All functions in this module are synchronous because they run once before the application start,
# so speed is irrelevant.
# Their being synchronous enables us to include them into BotData.__init__() without workarounds.
import json
import logging

import httpx

from samanthas_telegram_bot.api_queries import PREFIX
from samanthas_telegram_bot.conversation.data_structures.enums import AgeRangeType
from samanthas_telegram_bot.conversation.data_structures.helper_classes import (
    AgeRange,
    Assessment,
    AssessmentQuestion,
    AssessmentQuestionOption,
    DayAndTimeSlot,
)

logger = logging.getLogger(__name__)


def get_age_ranges() -> dict[AgeRangeType, tuple[AgeRange, ...]]:
    """Gets age ranges, assigns IDs (for bot phrases) to age ranges for teacher.

    The bot asks the teacher about students' ages, adding words like "teenager" or "adult"
    to the number ranges (e.g. "children (5-11)", in user's language).
    These words have to be assigned to these age ranges for the bot to display the correct phrase.
    For example: `phrases.csv` contains the phrase with ID ``option_adults``, so the age range
    corresponding to adults has to be assigned ``bot_phrase_id: option_adults``.
    """
    logger.info("Getting age ranges from the backend...")

    # this operation is run at application startup, so no exception handling needed
    r = httpx.get(f"{PREFIX}/age_ranges/")

    data = json.loads(r.content)
    logger.info("... age ranges loaded successfully.")

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
    """Gets assessment questions, based on language.

    Returns a dictionary matching an age range ID to assessment.

    Note: this is a **synchronous** function because it runs once before the application start.
    It being synchronous enables us to include it into ``BotData.__init__()``
    """

    logger.info(f"Getting assessment questions for {lang_code=}...")

    # this operation is run at application startup, so no exception handling needed
    r = httpx.get(f"{PREFIX}/enrollment_test/", params={"language": lang_code})

    data = json.loads(r.content)

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
    logger.info(f"... received {len(assessments)} assessments for {lang_code=}.")

    # Each assessment has a sequence of age range IDs. We have to match every single age range ID
    # in this sequence to a respective assessment.
    assessment_for_age_range_id = {
        age_range_id: assessment
        for assessment in assessments
        for age_range_id in assessment.age_range_ids
    }

    return assessment_for_age_range_id


def get_day_and_time_slots() -> tuple[DayAndTimeSlot, ...]:
    """Gets day and time slots.

    Note: this is a **synchronous** function because it runs once before the application start.
    It being synchronous enables us to include it into ``BotData.__init__()``
    """

    def get_hour(str_: str) -> int:
        """Takes a string like 05:00:00 and returns hours (5 in this example)."""
        return int(str_.split(":")[0])

    logger.info("Getting day and time slots...")

    # this operation is run at application startup, so no exception handling needed
    r = httpx.get(f"{PREFIX}/day_and_time_slots/")

    data = json.loads(r.content)

    logger.info(f"... received {len(data)} day and time slots.")

    return tuple(
        DayAndTimeSlot(
            id=item["id"],
            day_of_week_index=item["day_of_week_index"],
            from_utc_hour=get_hour(item["time_slot"]["from_utc_hour"]),
            to_utc_hour=get_hour(item["time_slot"]["to_utc_hour"]),
        )
        for item in data
    )
