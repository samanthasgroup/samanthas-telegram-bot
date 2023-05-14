from typing import TypedDict, cast

from samanthas_telegram_bot.api_queries import get_age_ranges, get_assessments
from samanthas_telegram_bot.conversation.auxil.load_phrases import load_phrases
from samanthas_telegram_bot.conversation.data_structures.enums import AgeRangeType


# using TypedDict for phrases to allow simple dict-like usage with dynamically determined locale
class MultilingualBotPhrase(TypedDict):
    en: str
    ru: str
    ua: str


class BotData:
    def __init__(self) -> None:
        self.age_ranges_for_type = get_age_ranges()
        self.assessment_for_age_range_id = get_assessments(lang_code="en")

        self.phrases = cast(dict[str, MultilingualBotPhrase], load_phrases())
        """Matches internal ID of a bot phrase to localized versions of this phrase."""

        self.student_ages_for_age_range_id = {
            age_range.id: age_range for age_range in self.age_ranges_for_type[AgeRangeType.STUDENT]
        }
        """Matches IDs of students' age ranges to the same `AgeRange` objects."""
