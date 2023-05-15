"""Various dataclasses, NamedTuples and TypedDicts for attribute hinting and easy unpacking.

The module is called helper_classes to distinguish it from context_types module that also contains
custom classes for attribute hinting, but related to inner workings of python-telegram-bot.
"""
from dataclasses import dataclass
from typing import NamedTuple, Optional, TypedDict

from samanthas_telegram_bot.conversation.data_structures.enums import AgeRangeType


@dataclass
class AgeRange:
    id: int
    age_from: int
    age_to: int
    type: AgeRangeType
    bot_phrase_id: Optional[str] = None


@dataclass
class AssessmentAnswer:
    # Those will be numbers, but both CallbackData and API work with strings,
    # and no math operations are performed, so no need to convert back and forth.
    question_id: str
    answer_id: str


class AssessmentQuestionOption(NamedTuple):
    id: int
    text: str


class AssessmentQuestion(NamedTuple):
    id: int
    text: str
    options: tuple[AssessmentQuestionOption, ...]


class Assessment(NamedTuple):
    id: int
    age_range_ids: tuple[int, ...]
    questions: tuple[AssessmentQuestion, ...]


# using TypedDict for phrases to allow simple dict-like usage with dynamically determined locale
class MultilingualBotPhrase(TypedDict):
    en: str
    ru: str
    ua: str


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
