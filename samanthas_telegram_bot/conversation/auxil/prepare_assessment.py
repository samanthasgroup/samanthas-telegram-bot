import logging

from telegram import CallbackQuery

from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender,
)
from samanthas_telegram_bot.conversation.data_structures.context_types import CUSTOM_CONTEXT_TYPES

logger = logging.getLogger(__name__)


async def prepare_assessment(context: CUSTOM_CONTEXT_TYPES, query: CallbackQuery) -> None:
    """Performs necessary preparatory operations and sends reply with CallbackQueryReplySender."""
    # prepare questions and set index to 0
    age_range_id = context.user_data.student_age_range_id
    logger.info(
        f"Using assessment for {age_range_id=} ({context.user_data.student_age_from}-"
        f"{context.user_data.student_age_to} years old)"
    )
    context.user_data.student_assessment = context.bot_data.assessment_for_age_range_id[
        age_range_id
    ]
    context.chat_data.current_assessment_question_index = 0
    context.chat_data.current_assessment_question_id = (
        context.user_data.student_assessment.questions[0].id
    )
    await CallbackQueryReplySender.ask_start_assessment(context, query)
