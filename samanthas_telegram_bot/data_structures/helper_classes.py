"""Various dataclasses, NamedTuples and TypedDicts for attribute hinting and easy unpacking.

The module is called helper_classes to distinguish it from context_types module that also contains
custom classes for attribute hinting, but related to inner workings of python-telegram-bot.
"""
from dataclasses import dataclass
from typing import NamedTuple, Optional, TypedDict

from samanthas_telegram_bot.data_structures.enums import AgeRangeType, SmalltalkTestStatus


@dataclass
class AgeRange:
    id: int
    age_from: int
    age_to: int
    type: AgeRangeType
    bot_phrase_id: Optional[str] = None


@dataclass
class AssessmentAnswer:
    question_id: int
    answer_id: int


class AssessmentQuestionOption(NamedTuple):
    id: int
    text: str

    def means_user_does_not_know_the_answer(self) -> bool:
        return "i don't know" in self.text.lower()


class AssessmentQuestion(NamedTuple):
    id: int
    text: str
    options: tuple[AssessmentQuestionOption, ...]


class Assessment(NamedTuple):
    id: int
    age_range_ids: tuple[int, ...]
    questions: tuple[AssessmentQuestion, ...]


@dataclass
class DayAndTimeSlot:
    id: int
    day_of_week_index: int
    from_utc_hour: int
    to_utc_hour: int


class LanguageAndLevel(NamedTuple):
    id: int
    language_id: str
    level: str


# using TypedDict for phrases to allow simple dict-like usage with dynamically determined locale
class MultilingualBotPhrase(TypedDict):
    en: str
    ru: str
    ua: str


class SmalltalkResult(NamedTuple):
    status: SmalltalkTestStatus
    level: str | None = None
    url: str | None = None
    original_json: bytes | None = None


@dataclass
class TeacherPeerHelp:
    """A class that comprises boolean flags for experienced teachers' willingness to help their
    peers.
    """

    # names of these flags match (parts of) IDs of phrases in phrases.csv and callback data
    can_check_syllabus: bool | None = None
    can_give_feedback: bool | None = None
    can_help_with_children_group: bool | None = None
    can_provide_materials: bool | None = None
    can_host_mentoring_sessions: bool | None = None
    can_invite_to_class: bool | None = None
    can_work_in_tandem: bool | None = None
