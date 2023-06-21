"""Various dataclasses and TypedDicts for attribute hinting and easy unpacking.

Most of the classes correspond to models in the backend.
"""
from dataclasses import dataclass
from typing import Optional, TypedDict

from samanthas_telegram_bot.api_queries.auxil.constants import DataDict
from samanthas_telegram_bot.data_structures.constants import WEEKDAYS
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


@dataclass(frozen=True)
class AssessmentQuestionOption:
    id: int
    text: str

    def means_user_does_not_know_the_answer(self) -> bool:
        return "i don't know" in self.text.lower()


@dataclass(frozen=True)
class AssessmentQuestion:
    id: int
    text: str
    options: tuple[AssessmentQuestionOption, ...]


@dataclass(frozen=True)
class Assessment:
    id: int
    age_range_ids: tuple[int, ...]
    questions: tuple[AssessmentQuestion, ...]


@dataclass
class DayAndTimeSlot:
    id: int
    day_of_week_index: int
    from_utc_hour: int
    to_utc_hour: int

    def __str__(self) -> str:
        return f"{WEEKDAYS[self.day_of_week_index]} {self.from_utc_hour}-{self.to_utc_hour} UTC"


@dataclass(frozen=True)
class LanguageAndLevel:
    id: int
    language_id: str
    level: str


# using TypedDict for phrases to allow simple dict-like usage with dynamically determined locale
class MultilingualBotPhrase(TypedDict):
    en: str
    ru: str
    ua: str


@dataclass(frozen=True)
class SmalltalkResult:
    status: SmalltalkTestStatus
    level: str | None = None
    url: str | None = None
    json: DataDict | None = None


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
