import logging

from telegram import Update

from samanthas_telegram_bot.api_queries import send_written_answers_get_level
from samanthas_telegram_bot.assessment import prepare_assessment
from samanthas_telegram_bot.callbacks.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.callbacks.auxil.message_sender import MessageSender
from samanthas_telegram_bot.callbacks.auxil.utils import answer_callback_query_and_get_data
from samanthas_telegram_bot.constants import CallbackData, State
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES

logger = logging.getLogger(__name__)


async def store_communication_language_ask_non_teaching_help_or_start_review(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores communication language, asks about non-teaching help or starts review.

    This callback is intended for students only.
    If a student is 15 or older, asks about additional help. Otherwise, proceeds to review.
    """
    (
        query,
        context.user_data.communication_language_in_class,
    ) = await answer_callback_query_and_get_data(update)

    if context.user_data.student_age_from >= 15:
        await CQReplySender.ask_non_teaching_help(context, query)
        return State.NON_TEACHING_HELP_MENU_OR_PEER_HELP_FOR_TEACHER_OR_REVIEW_FOR_STUDENT

    await MessageSender.ask_review(update, context)
    return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT


async def ask_communication_language_or_start_assessment_depending_on_learning_experience(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Starts assessment or asks for additional help the student requires. No data is stored here.

    * For students that have been learning English for 1 year or more, starts assessment.
    * For students that have been learning English for less than 1 year, stores that they
      need an oral interview (skipping the assessment). Then asks about communication language.
    """
    query, data = await answer_callback_query_and_get_data(update)

    if data == "year_or_more":
        await prepare_assessment(context, query)
        return State.ASK_ASSESSMENT_QUESTION

    context.user_data.student_needs_oral_interview = True

    await CQReplySender.ask_class_communication_languages(context, query)
    return State.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW


async def assessment_store_answer_ask_question(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores answer to the question (unless this is the beginning of the test), asks next one."""
    query, data = await answer_callback_query_and_get_data(update)

    if (
        context.chat_data["current_question_idx"]
        == len(context.chat_data["assessment_questions"]) - 1
    ):
        level = await send_written_answers_get_level({}, logger)  # TODO
        if level == "A2":  # TODO
            pass
        else:
            # TODO add some encouragement message on completing the test?
            await CQReplySender.ask_class_communication_languages(context, query)
            return State.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW

    if data in ("1", "2", "3", "4", CallbackData.DONT_KNOW):
        # TODO store
        context.chat_data["current_question_idx"] += 1

    await CQReplySender.ask_next_assessment_question(context, query)
    return State.ASK_ASSESSMENT_QUESTION
