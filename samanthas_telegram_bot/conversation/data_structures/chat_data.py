from dataclasses import dataclass

from samanthas_telegram_bot.conversation.data_structures.enums import ConversationMode


@dataclass
class ChatData:
    """Class for data only relevant for one particular conversation."""

    current_assessment_question_index: int | None = None
    current_assessment_question_id: str | None = None
    day_index: int | None = None
    mode: ConversationMode | None = None
    peer_help_callback_data: set[str] | None = None
