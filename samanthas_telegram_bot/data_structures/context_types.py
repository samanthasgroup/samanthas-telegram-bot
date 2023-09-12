"""Module with context types to be used with python-telegram-bot instead of plain dictionaries."""
import json
from dataclasses import dataclass

from telegram import Update
from telegram.ext import CallbackContext, ExtBot

from samanthas_telegram_bot.api_clients.auxil.constants import DataDict
from samanthas_telegram_bot.conversation.auxil.enums import ConversationMode
from samanthas_telegram_bot.data_structures.enums import AgeRangeType, Role
from samanthas_telegram_bot.data_structures.literal_types import CommunicationModeInClass, Locale
from samanthas_telegram_bot.data_structures.models import (
    AgeRange,
    Assessment,
    AssessmentAnswer,
    DayAndTimeSlot,
    LanguageAndLevel,
    MultilingualBotPhrase,
    SmalltalkResult,
    TeacherPeerHelp,
)


@dataclass
class BotData:
    """Class for bot-level data needed for every conversation."""

    age_ranges_for_type: dict[AgeRangeType, tuple[AgeRange, ...]] | None = None
    assessment_for_age_range_id: dict[int, Assessment] | None = None

    conversation_mode_for_chat_id: dict[int, ConversationMode] | None = None
    """Used to store conversation modes each chat is in. This data cannot be stored
    in individual ``chat_id`` because ``.chat_id`` will be different for different contexts
    (e.g. the one for handling Telegram updates and the one for handling Chatwoot updates).
    
    Note: this attribute is **not** updated from backend and is kept in bot's persistence.  
    """

    day_and_time_slot_for_slot_id: dict[int, DayAndTimeSlot] | None = None
    """Matches IDs of DayAndTimeSlot objects to DayAndTimeSLot objects themselves.
    Needed for matching callback data to entire objects (e.g. to show the user later on
    what they have chosen)
     """

    day_and_time_slots_for_day_index: dict[int, tuple[DayAndTimeSlot, ...]] | None = None
    """Matches indexes of days of the week to `DayAndTimeSlot` objects. We ask the user
    time slots day by day, so for each day we have to select slots with the correct day index.
     """

    sorted_language_ids: list[str] | None = None
    """Language IDs sorted by language code (but English always comes first)."""

    language_and_level_for_id: dict[int, LanguageAndLevel] | None = None
    """Matches IDs of `LanguageAndLevel` objects to same `LanguageAndLevel` objects."""

    # naming with "_objects" to avoid ambiguity of "languages_and_levels"
    language_and_level_objects_for_language_id: dict[
        str, tuple[LanguageAndLevel, ...]
    ] | None = None
    """Matches IDs of teaching languages (strings like "en", "de" etc.) to tuples
    of corresponding `LanguageAndLevel` objects."""

    language_and_level_id_for_language_id_and_level: dict[tuple[str, str], int] | None = None
    """Matches a tuple of language_id and level to an ID of `LanguageAndLevel` object.
    This ID (or these IDs) will be passed to the backend."""

    # self.phrase_for_id or even self.multilingual_phrase_for_id would be more accurate,
    # but it's used so often that it's better to keep the name as short as possible.
    phrases: dict[str, MultilingualBotPhrase] | None = None
    """Matches internal ID of a bot phrase to localized versions of this phrase."""

    student_ages_for_age_range_id: dict[int, AgeRange] | None = None
    """Matches IDs of students' age ranges to the same `AgeRange` objects."""


@dataclass
class ChatData:
    """Class for data only relevant for one particular conversation."""

    # assessment flow
    assessment: Assessment | None = None
    current_assessment_question_index: int | None = None
    current_assessment_question_id: int | None = None
    day_index: int | None = None

    # for tracking "Don't know"s during assessment
    assessment_dont_knows_in_a_row: int | None = None
    ids_of_dont_know_options_in_assessment: set[int] | None = None
    """IDs of all question options whose text is 'I don't know'."""

    # misc
    peer_help_callback_data: set[str] | None = None
    """Names of callback data for peer help types selected by the user. It is not passed
    to the backend, only used to control the buttons and check number of options selected. 
    """


@dataclass
class UserData:
    """Class for data pertaining to the user that will be sent to backend."""

    STATUS_AT_CREATION_STUDENT_TEACHER = "no_group_yet"

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
    """A dictionary for languages and levels, used for building messages and keyboards."""
    language_and_level_ids: list[int] | None = None
    """A list of `LanguageAndLevel` IDs to be passed to backend."""
    communication_language_in_class: CommunicationModeInClass | None = None
    # This will be a list as opposed to peer help that is a bunch of boolean flags, because IDs of
    # help types are fixed between back-end and bot anyway (they are used for bot phrases).
    non_teaching_help_types: list[str] | None = None
    comment: str | None = None

    helpdesk_conversation_id: int | None = None
    """Conversation ID received from the helpdesk platform (currently Chatwoot) after registration 
    to connect coordinator there to the person communicating with the bot.
    """

    # role-specific attributes:
    student_age_range_id: int | None = None  # for passing back to backend
    student_age_from: int | None = None  # for assessment
    student_age_to: int | None = None  # for assessment
    student_assessment_answers: list[AssessmentAnswer] | None = None
    student_assessment_resulting_level: str | None = None
    student_can_read_in_english: bool | None = None
    student_agreed_to_smalltalk: bool | None = None
    student_smalltalk_test_id: str | None = None
    student_smalltalk_interview_url: str | None = None
    student_smalltalk_result: SmalltalkResult | None = None
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

    def clear_student_data(self) -> None:
        """Sets all student-related attributes to ``None``. This may be needed because multiple
        students can be registered from one device.
        """
        # clear all student-related attributes, make sure not to touch methods
        for attr in (
            attr
            for attr in dir(self)
            if attr.startswith("student_") and not callable(getattr(self, attr))
        ):
            setattr(self, attr, None)

    def personal_info_as_dict(self) -> DataDict:
        return {
            "communication_language_mode": self.communication_language_in_class,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "telegram_username": self.tg_username or "",
            "email": self.email,
            "phone": self.phone_number,
            "utc_timedelta": f"{self.utc_offset_hour:02d}:{self.utc_offset_minute}:00",
            "information_source": self.source,
            "registration_telegram_bot_chat_id": self.chat_id,
            "registration_telegram_bot_language": self.locale,
            "chatwoot_conversation_id": self.helpdesk_conversation_id,
        }

    def student_as_dict(self, update: Update, personal_info_id: int) -> DataDict:
        data: DataDict = {
            "personal_info": personal_info_id,
            "comment": self.comment,
            "project_status": self.STATUS_AT_CREATION_STUDENT_TEACHER,
            "status_since": self._format_status_since(update),
            "can_read_in_english": self.student_can_read_in_english,
            "is_member_of_speaking_club": False,  # TODO can backend set to False by default?
            "age_range": self.student_age_range_id,
            "availability_slots": self.day_and_time_slot_ids,
            "non_teaching_help_required": self.non_teaching_help_types,
            "teaching_languages_and_levels": self.language_and_level_ids,
        }
        if self.student_smalltalk_result:
            data["smalltalk_test_result"] = json.dumps(self.student_smalltalk_result.json)
            # TODO url (when field in backend is created)
        return data

    def student_enrollment_test_as_dict(self, personal_info_id: int) -> DataDict:
        if self.student_assessment_answers is None:
            raise TypeError(
                "Don't pass user_data with no student assessment answers to this method"
            )
        return {
            "student": personal_info_id,
            "answers": [item.answer_id for item in self.student_assessment_answers],
        }

    def teacher_as_dict(self, update: Update, personal_info_id: int) -> DataDict:
        peer_help = self.teacher_peer_help

        return {
            "personal_info": personal_info_id,
            "comment": self.comment,
            "project_status": self.STATUS_AT_CREATION_STUDENT_TEACHER,
            "status_since": self._format_status_since(update),
            "can_host_speaking_club": self.teacher_can_host_speaking_club,
            "has_hosted_speaking_club": False,
            "is_validated": False,
            "has_prior_teaching_experience": self.teacher_has_prior_experience,
            "non_teaching_help_provided_comment": self.teacher_additional_skills_comment,
            "peer_support_can_check_syllabus": peer_help.can_check_syllabus,
            "peer_support_can_host_mentoring_sessions": peer_help.can_host_mentoring_sessions,
            "peer_support_can_give_feedback": peer_help.can_give_feedback,
            "peer_support_can_help_with_childrens_groups": peer_help.can_help_with_children_group,
            "peer_support_can_provide_materials": peer_help.can_provide_materials,
            "peer_support_can_invite_to_class": peer_help.can_invite_to_class,
            "peer_support_can_work_in_tandem": peer_help.can_work_in_tandem,
            "simultaneous_groups": self.teacher_number_of_groups,
            "weekly_frequency_per_group": self.teacher_class_frequency,
            "availability_slots": self.day_and_time_slot_ids,
            "non_teaching_help_provided": self.non_teaching_help_types,
            "student_age_ranges": self.teacher_student_age_range_ids,
            "teaching_languages_and_levels": self.language_and_level_ids,
        }

    def teacher_under_18_as_dict(self, update: Update, personal_info_id: int) -> DataDict:
        return {
            "personal_info": personal_info_id,
            "comment": self.comment,
            "status_since": self._format_status_since(update),
            "project_status": self.STATUS_AT_CREATION_STUDENT_TEACHER,
            "can_host_speaking_club": self.teacher_can_host_speaking_club,
            "has_hosted_speaking_club": False,
            "is_validated": False,
            "non_teaching_help_provided_comment": self.teacher_additional_skills_comment,
            "teaching_languages_and_levels": self.language_and_level_ids,
        }

    @staticmethod
    def _format_status_since(update: Update) -> str:
        """Converts a datetime object into suitable format for `status_since` field."""
        # TODO can/should backend do this?
        return update.effective_message.date.isoformat().replace("+00:00", "Z")


# Include custom classes into ContextTypes to get attribute hinting (replacing standard dicts with
# UserData for "user_data" etc.).
CUSTOM_CONTEXT_TYPES = CallbackContext[ExtBot[None], UserData, ChatData, BotData]
