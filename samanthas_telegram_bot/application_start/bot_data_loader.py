"""Functionality for API queries and other operations necessary for loading BotData."""

import csv
import logging
import typing
from pathlib import Path

from samanthas_telegram_bot.api_clients import BackendClient
from samanthas_telegram_bot.data_structures.constants import LOCALES
from samanthas_telegram_bot.data_structures.context_types import BotData
from samanthas_telegram_bot.data_structures.enums import AgeRangeType
from samanthas_telegram_bot.data_structures.models import (
    AgeRange,
    Assessment,
    AssessmentQuestion,
    AssessmentQuestionOption,
    DayAndTimeSlot,
    LanguageAndLevel,
    MultilingualBotPhrase,
)

logger = logging.getLogger(__name__)


class BotDataLoader:
    """Class for loading bot data from backend or external files.

    Should be called in Application.post_init() to refresh data that were loaded from persistence.
    """

    @classmethod
    def load(cls, bot_data: BotData) -> None:
        """Load bot data from backend or external file(s)."""

        logger.info("Loading data for bot initialization from backend")

        bot_data.age_ranges_for_type = cls._get_age_ranges()

        bot_data.assessment_for_age_range_id = cls._get_assessments(lang_code="en")

        day_and_time_slots = cls._get_day_and_time_slots()
        bot_data.day_and_time_slot_for_slot_id = {slot.id: slot for slot in day_and_time_slots}
        bot_data.day_and_time_slots_for_day_index = {
            index: tuple(slot for slot in day_and_time_slots if slot.day_of_week_index == index)
            for index in range(7)
        }

        languages_and_levels = cls._get_languages_and_levels()
        unique_language_ids = {item.language_id for item in languages_and_levels}
        bot_data.sorted_language_ids = ["en"] + sorted(unique_language_ids - {"en"})
        bot_data.language_and_level_for_id = {item.id: item for item in languages_and_levels}
        bot_data.language_and_level_objects_for_language_id = {
            language_id: tuple(
                language_and_level
                for language_and_level in languages_and_levels
                if language_and_level.language_id == language_id
            )
            for language_id in bot_data.sorted_language_ids
        }
        bot_data.language_and_level_id_for_language_id_and_level = {
            (item.language_id, item.level): item.id for item in languages_and_levels
        }

        bot_data.phrases = cls._load_phrases()

        bot_data.student_ages_for_age_range_id = {
            age_range.id: age_range
            for age_range in bot_data.age_ranges_for_type[AgeRangeType.STUDENT]
        }

        # initialize dictionary if nothing was loaded from persistence
        if bot_data.conversation_mode_for_chat_id is None:
            bot_data.conversation_mode_for_chat_id = {}

    @classmethod
    def _get_age_ranges(cls) -> dict[AgeRangeType, tuple[AgeRange, ...]]:
        """Get age ranges from the backend, assign IDs (for bot phrases) to age ranges for teacher.

        Reasoning for assigning bot phrase IDs to age ranges: Bot asks the teacher about students'
        ages, adding words like "teenager" or "adult" to the number ranges (e.g. "children (5-11)",
        in user's language).

        These words have to be assigned to these age ranges for bot to display the correct phrase.
        For example: `phrases.csv` contains the phrase with ID ``option_adults``, so the age range
        corresponding to adults has to be assigned ``bot_phrase_id: option_adults``.
        """

        logger.info("Loading age ranges")
        data = BackendClient.get_age_ranges()

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

    @classmethod
    def _get_assessments(cls, lang_code: str) -> dict[int, Assessment]:
        """Gets assessment questions from the backend, based on language.

        Returns a dictionary matching an age range ID to assessment.
        """

        logger.info(f"Loading assessments for {lang_code=}")
        data = BackendClient.get_assessments(lang_code=lang_code)

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

        # Each assessment has a sequence of age range IDs. We must match every single age range ID
        # in this sequence to a respective assessment.
        assessment_for_age_range_id = {
            age_range_id: assessment
            for assessment in assessments
            for age_range_id in assessment.age_range_ids
        }

        return assessment_for_age_range_id

    @classmethod
    def _get_day_and_time_slots(cls) -> tuple[DayAndTimeSlot, ...]:
        """Gets day and time slots from the backend."""

        def get_hour(str_: str) -> int:
            """Takes a string like 05:00:00 and returns hours (5 in this example)."""
            return int(str_.split(":")[0])

        logger.info("Loading day and time slots")
        data = BackendClient.get_day_and_time_slots()

        return tuple(
            DayAndTimeSlot(
                id=item["id"],
                day_of_week_index=item["day_of_week_index"],
                from_utc_hour=get_hour(item["time_slot"]["from_utc_hour"]),
                to_utc_hour=get_hour(item["time_slot"]["to_utc_hour"]),
            )
            for item in data
        )

    @classmethod
    def _get_languages_and_levels(cls) -> tuple[LanguageAndLevel, ...]:
        """Gets languages and levels from the backend."""

        logger.info("Loading languages and levels")
        data = BackendClient.get_languages_and_levels()

        return tuple(
            LanguageAndLevel(
                id=item["id"], language_id=item["language"]["id"], level=item["level"]
            )
            for item in data
        )

    @staticmethod
    def _load_phrases() -> dict[str, MultilingualBotPhrase]:
        """Reads bot phrases from CSV file, returns dictionary with internal IDs as key,
        and a subclass of `TypedDict` as value, matching locales to actual phrases.
        """

        logger.info("Loading bot phrases")
        with (Path(__file__).parent.resolve() / "phrases.csv").open(
            encoding="utf-8", newline=""
        ) as f:
            reader = typing.cast(typing.Iterator[dict[str, str]], csv.DictReader(f))
            return {
                row["internal_id"]: MultilingualBotPhrase(
                    **{
                        locale: row[locale].replace("\\n", "\n")  # type: ignore[typeddict-item]
                        for locale in LOCALES
                    }
                )
                for row in reader
            }
