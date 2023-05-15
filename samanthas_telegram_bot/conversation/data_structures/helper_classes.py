"""Various `dataclasses, NamedTuples and TypedDicts for attribute hinting and easy unpacking.

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
