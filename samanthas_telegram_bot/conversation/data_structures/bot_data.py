import logging
import typing
from typing import TypedDict

from samanthas_telegram_bot.conversation.auxil.load_phrases import load_phrases

logger = logging.getLogger(__name__)


# using TypedDict for phrases to allow simple dict-like usage with dynamically determined locale
class MultilingualBotPhrase(TypedDict):
    en: str
    ru: str
    ua: str


class BotData:
    def __init__(self) -> None:
        logger.info("Loading bot phrases")
        self.phrases = typing.cast(dict[str, MultilingualBotPhrase], load_phrases())
        """Matches internal ID of a bot phrase to localized versions of this phrase."""
