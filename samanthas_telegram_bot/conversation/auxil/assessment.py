from telegram import CallbackQuery

from samanthas_telegram_bot.api_queries import get_assessment_questions
from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender,
)
from samanthas_telegram_bot.conversation.custom_context_types import CUSTOM_CONTEXT_TYPES


async def prepare_assessment(context: CUSTOM_CONTEXT_TYPES, query: CallbackQuery) -> None:
    """Performs necessary preparatory operations and sends reply with CallbackQueryReplySender."""
    # prepare questions and set index to 0
    context.chat_data["assessment_questions"] = get_assessment_questions("en")  # TODO add age
    context.chat_data["current_question_idx"] = 0
    await CallbackQueryReplySender.ask_start_assessment(context, query)
