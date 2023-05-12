from telegram import CallbackQuery

from samanthas_telegram_bot.api_queries import get_assessment_questions
from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender,
)
from samanthas_telegram_bot.conversation.data_structures.custom_context_types import (
    CUSTOM_CONTEXT_TYPES,
)


async def prepare_assessment(context: CUSTOM_CONTEXT_TYPES, query: CallbackQuery) -> None:
    """Performs necessary preparatory operations and sends reply with CallbackQueryReplySender."""
    # prepare questions and set index to 0
    assessment_id, context.chat_data["assessment_questions"] = await get_assessment_questions(
        lang_code="en",
        age_range_id=context.user_data.student_age_range_id,
    )
    context.user_data.student_assessment_id = assessment_id
    context.chat_data["current_question_index"] = 0
    context.chat_data["current_question_id"] = context.chat_data["assessment_questions"][0]["id"]
    await CallbackQueryReplySender.ask_start_assessment(context, query)
