from typing import TypedDict, cast

from samanthas_telegram_bot.api_queries import get_age_ranges, get_assessments
from samanthas_telegram_bot.conversation.auxil.load_phrases import load_phrases


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
