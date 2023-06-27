from telegram import CallbackQuery, Update

from samanthas_telegram_bot.api_queries.auxil.enums import LoggingLevel
from samanthas_telegram_bot.api_queries.backend_client import BackendClient
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender,
)
from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.enums import ConversationStateStudent
from samanthas_telegram_bot.conversation.auxil.helpers import answer_callback_query_and_get_data
from samanthas_telegram_bot.data_structures.constants import LEVELS_ELIGIBLE_FOR_ORAL_TEST
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES


async def prepare_assessment(context: CUSTOM_CONTEXT_TYPES, query: CallbackQuery) -> None:
    """Performs necessary preparatory operations and sends reply with CallbackQueryReplySender."""
    # prepare questions and set index to 0
    age_range_id = context.user_data.student_age_range_id
    await logs(
        bot=context.bot,
        level=LoggingLevel.INFO,
        text=(
            f"Using assessment for {age_range_id=} ({context.user_data.student_age_from}-"
            f"{context.user_data.student_age_to} years old)"
        ),
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


async def process_results(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Processes results of a written assessment, returns appropriate next conversation state."""
    query, _ = await answer_callback_query_and_get_data(update)

    context.user_data.student_assessment_resulting_level = (
        await BackendClient.get_level_of_written_test(update, context)
    )
    if context.user_data.student_assessment_resulting_level in LEVELS_ELIGIBLE_FOR_ORAL_TEST:
        await CQReplySender.ask_yes_no(
            context,
            query,
            question_phrase_internal_id="ask_student_start_oral_test",
            parse_mode=None,
        )
        return ConversationStateStudent.SEND_SMALLTALK_URL_OR_ASK_COMMUNICATION_LANGUAGE
    else:
        # TODO add some compliment on completing the test even without oral test?
        context.user_data.language_and_level_ids = [
            context.bot_data.language_and_level_id_for_language_id_and_level[
                ("en", context.user_data.student_assessment_resulting_level)
            ]
        ]
        await CQReplySender.ask_class_communication_languages(context, query)
        return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW
