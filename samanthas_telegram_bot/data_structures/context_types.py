"""Module with context types to be used with python-telegram-bot instead of plain dictionaries."""
from dataclasses import dataclass
from typing import Literal, cast

from telegram.ext import CallbackContext, ExtBot

from samanthas_telegram_bot.conversation.auxil.load_phrases import load_phrases
from samanthas_telegram_bot.data_structures.constants import Locale
from samanthas_telegram_bot.data_structures.enums import AgeRangeType, ConversationMode, Role
from samanthas_telegram_bot.data_structures.helper_classes import (
    Assessment,
    AssessmentAnswer,
    DayAndTimeSlot,
    LanguageAndLevel,
    MultilingualBotPhrase,
    TeacherPeerHelp,
)


class BotData:
    """Class for data needed for every conversation and get loaded once at application start."""

    def __init__(self) -> None:
        # can't be imported at top of the module: it will lead to circular import error
        from samanthas_telegram_bot.api_queries.bot_start import (
            get_age_ranges,
            get_assessments,
            get_day_and_time_slots,
            get_languages_and_levels,
        )

        self.age_ranges_for_type = get_age_ranges()
        self.assessment_for_age_range_id = get_assessments(lang_code="en")

        day_and_time_slots = get_day_and_time_slots()

        self.day_and_time_slot_for_slot_id: dict[int, DayAndTimeSlot] = {
            slot.id: slot for slot in day_and_time_slots
        }
        """Matches IDs of DayAndTimeSlot objects to DayAndTimeSLot objects themselves.
        Needed for matching callback data to entire objects (e.g. to show the user later on
        what they have chosen)
         """

        self.day_and_time_slots_for_day_index: dict[int, tuple[DayAndTimeSlot, ...]] = {
            index: tuple(slot for slot in day_and_time_slots if slot.day_of_week_index == index)
            for index in range(7)
        }
        """Matches indexes of days of the week to DayAndTimeSlot objects. We ask the user
        time slots day by day, so for each day we have to select slots with the correct day index.
         """

        languages_and_levels = get_languages_and_levels()
        unique_language_ids = {item.language_id for item in languages_and_levels}

        # make sure English comes first as it has to be displayed first to the user
        self.sorted_language_ids = ["en"] + sorted(unique_language_ids - {"en"})
        """Language IDs sorted by language code (but English always comes first)."""

        self.language_and_level_for_id: dict[int, LanguageAndLevel] = {
            item.id: item for item in languages_and_levels
        }
        """Matches IDs of `LanguageAndLevel` objects to same `LanguageAndLevel` objects."""

        self.language_and_level_objects_for_language_id: dict[
            str, tuple[LanguageAndLevel, ...]
        ] = {
            language_id: tuple(
                language_and_level
                for language_and_level in languages_and_levels
                if language_and_level.language_id == language_id
            )
            for language_id in self.sorted_language_ids
        }
        """Matches IDs of languages (strings like "en", "de" etc.) to sequences of corresponding
        `LanguageAndLevel` objects."""

        self.phrases = cast(dict[str, MultilingualBotPhrase], load_phrases())
        """Matches internal ID of a bot phrase to localized versions of this phrase."""

        self.student_ages_for_age_range_id = {
            age_range.id: age_range for age_range in self.age_ranges_for_type[AgeRangeType.STUDENT]
        }
        """Matches IDs of students' age ranges to the same `AgeRange` objects."""


@dataclass
class ChatData:
    """Class for data only relevant for one particular conversation."""

    current_assessment_question_index: int | None = None
    current_assessment_question_id: str | None = None
    day_index: int | None = None
    mode: ConversationMode | None = None
    peer_help_callback_data: set[str] | None = None


@dataclass
class UserData:
    """Class for data pertaining to the user that will be sent to backend."""

    # TODO sets instead of lists?
    locale: Locale | None = None
    chat_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    source: str | None = None
    tg_username: str | None = None
    phone_number: str | None = None
    email: str | None = None
    role: Role | None = None
    # no datetime objects are needed to achieve results needed for the bot
    utc_offset_hour: int | None = None
    utc_offset_minute: int | None = None
    day_and_time_slot_ids: list[int] | None = None
    levels_for_teaching_language: dict[str, list[str]] | None = None
    communication_language_in_class: Literal["en", "ru", "ua"] | None = None
    # This will be a list as opposed to peer help that is a bunch of boolean flags, because IDs of
    # help types are fixed between back-end and bot anyway (they are used for bot phrases).
    non_teaching_help_types: list[str] | None = None
    comment: str | None = None

    # role-specific attributes:
    student_age_range_id: int | None = None  # for passing back to backend
    student_age_from: int | None = None  # for assessment
    student_age_to: int | None = None  # for assessment
    student_assessment: Assessment | None = None
    student_assessment_answers = list[AssessmentAnswer]
    student_can_read_in_english: bool | None = None
    # False instead of None is intended, because the value is set based on other answers.
    # By default, the student doesn't need an oral interview before they are included
    # in a waiting list for the group matching algorithm.
    student_needs_oral_interview: bool | None = False
    teacher_is_under_18: bool | None = None
    teacher_has_prior_experience: bool | None = None
    teacher_number_of_groups: int | None = None
    teacher_class_frequency: int | None = None
    teacher_student_age_range_ids: list[int] | None = None
    teacher_can_host_speaking_club: bool | None = None
    teacher_peer_help = TeacherPeerHelp()
    teacher_additional_skills_comment: str | None = None


# Include custom classes into ContextTypes to get attribute hinting (replacing standard dicts with
# UserData for "user_data" etc.).
CUSTOM_CONTEXT_TYPES = CallbackContext[ExtBot[None], UserData, ChatData, BotData]
