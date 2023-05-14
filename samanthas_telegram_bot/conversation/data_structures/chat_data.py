from dataclasses import dataclass

from samanthas_telegram_bot.conversation.data_structures.age_range import AgeRange
from samanthas_telegram_bot.conversation.data_structures.enums import (
    AgeRangeType,
    ConversationMode,
)


@dataclass
class ChatData:
    age_ranges_for_type: dict[AgeRangeType, tuple[AgeRange]] | None = None
    current_assessment_question_index: int | None = None
    current_assessment_question_id: str | None = None
    day_index: int | None = None
    mode: ConversationMode | None = None
    peer_help_callback_data: set[str] | None = None
    student_ages_for_age_range_id: dict[int, AgeRange] | None = None
