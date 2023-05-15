"""Module with context types to be used with python-telegram-bot instead of plain dictionaries."""
from dataclasses import dataclass
from typing import Literal, cast

from telegram.ext import CallbackContext, ExtBot

from samanthas_telegram_bot.conversation.auxil.load_phrases import load_phrases
from samanthas_telegram_bot.conversation.data_structures.constants import Locale
from samanthas_telegram_bot.conversation.data_structures.enums import (
    AgeRangeType,
    ConversationMode,
    Role,
)
from samanthas_telegram_bot.conversation.data_structures.helper_classes import (
    Assessment,
    AssessmentAnswer,
    MultilingualBotPhrase,
    TeacherPeerHelp,
)


class BotData:
    """Class for data needed for every conversation and get loaded once at application start."""

    def __init__(self) -> None:
        # can't be imported at top of the module: it will lead to circular import error
        from samanthas_telegram_bot.api_queries import get_age_ranges, get_assessments

        self.age_ranges_for_type = get_age_ranges()
        self.assessment_for_age_range_id = get_assessments(lang_code="en")

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
    time_slots_for_day: dict | None = None  # type: ignore  # TODO use dataclass or TypedDict
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
