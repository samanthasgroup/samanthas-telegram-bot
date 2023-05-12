from dataclasses import dataclass
from typing import Optional

from samanthas_telegram_bot.conversation.data_structures.enums import AgeRangeType


@dataclass
class AgeRange:
    id: int
    age_from: int
    age_to: int
    type: AgeRangeType
    bot_phrase_id: Optional[str] = None
