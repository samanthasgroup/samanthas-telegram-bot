import logging

from telegram import CallbackQuery

from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender,
)
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES

logger = logging.getLogger(__name__)


async def prepare_assessment(context: CUSTOM_CONTEXT_TYPES, query: CallbackQuery) -> None:
    """Performs necessary preparatory operations and sends reply with CallbackQueryReplySender."""
    # prepare questions and set index to 0
    age_range_id = context.user_data.student_age_range_id
    logger.info(
        f"Using assessment for {age_range_id=} ({context.user_data.student_age_from}-"
        f"{context.user_data.student_age_to} years old)"
    )
    context.chat_data.assessment = context.bot_data.assessment_for_age_range_id[age_range_id]
    # TODO move to startup area? What happens if someone passes the test and then registers
    #  another user and chooses a different language?
    context.user_data.student_assessment_answers = []
    context.user_data.student_assessment_resulting_level = None
    context.user_data.student_agreed_to_smalltalk = False
    context.chat_data.current_assessment_question_index = 0
    context.chat_data.current_assessment_question_id = context.chat_data.assessment.questions[0].id
    context.chat_data.ids_of_dont_know_options_in_assessment = {
        option.id
        for question in context.chat_data.assessment.questions
        for option in question.options
        if option.means_user_does_not_know_the_answer()
    }
    context.chat_data.assessment_dont_knows_in_a_row = 0
    await CallbackQueryReplySender.ask_start_assessment(context, query)
