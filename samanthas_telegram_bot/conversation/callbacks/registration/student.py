import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.check import get_level_of_written_test
from samanthas_telegram_bot.api_queries.smalltalk import send_user_data_get_smalltalk_test
from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.conversation.auxil.prepare_assessment import prepare_assessment
from samanthas_telegram_bot.conversation.auxil.shortcuts import answer_callback_query_and_get_data
from samanthas_telegram_bot.data_structures.constants import LEVELS_ELIGIBLE_FOR_ORAL_TEST, Locale
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import CommonCallbackData, ConversationState
from samanthas_telegram_bot.data_structures.helper_classes import AssessmentAnswer

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
        return (
            ConversationState.NON_TEACHING_HELP_MENU_OR_PEER_HELP_FOR_TEACHER_OR_REVIEW_FOR_STUDENT
        )

    await MessageSender.ask_review(update, context)
    return ConversationState.REVIEW_MENU_OR_ASK_FINAL_COMMENT


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
        logger.info(
            f"Chat {update.effective_chat.id}. "
            f"Student has learned English for year or more. Starting assessment"
        )
        await prepare_assessment(context, query)
        return ConversationState.ASK_ASSESSMENT_QUESTION

    logger.info(
        f"Chat {update.effective_chat.id}. "
        f"Student has learned English for less than a year. Will need oral interview"
    )
    context.user_data.student_needs_oral_interview = True

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationState.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW


async def assessment_store_answer_ask_question(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores answer to the question (unless this is the beginning of the test), asks next one."""
    query, data = await answer_callback_query_and_get_data(update)

    if data not in (CommonCallbackData.ABORT, CommonCallbackData.OK):
        context.user_data.student_assessment_answers.append(
            AssessmentAnswer(
                question_id=context.chat_data.current_assessment_question_id,
                answer_id=int(data),
            )
        )

    # just starting the test: send first question
    if data == CommonCallbackData.OK:
        await CQReplySender.ask_next_assessment_question(context, query)
        return ConversationState.ASK_ASSESSMENT_QUESTION

    # get level if user has finished or aborted the test
    if (
        len(context.user_data.student_assessment_answers)
        == len(context.chat_data.assessment.questions)
    ) or data == CommonCallbackData.ABORT:
        context.user_data.student_assessment_resulting_level = await get_level_of_written_test(
            context=context,
        )
        if context.user_data.student_assessment_resulting_level in LEVELS_ELIGIBLE_FOR_ORAL_TEST:
            await CQReplySender.ask_yes_no(
                context,
                query,
                question_phrase_internal_id="ask_student_start_oral_test",
                parse_mode=None,
            )
            return ConversationState.SEND_SMALLTALK_URL_OR_ASK_COMMUNICATION_LANGUAGE
        else:
            # TODO add some compliment on completing the test even without oral test?
            context.user_data.language_and_level_ids = [
                context.bot_data.language_and_level_id_for_language_id_and_level[
                    ("en", context.user_data.student_assessment_resulting_level)
                ]
            ]
            await CQReplySender.ask_class_communication_languages(context, query)
            return ConversationState.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW

    if int(data) in context.chat_data.ids_of_dont_know_options_in_assessment:
        logger.debug(f"Chat {update.effective_chat.id}. User replied 'I don't know'")
        context.chat_data.assessment_dont_knows_in_a_row += 1
    else:
        context.chat_data.assessment_dont_knows_in_a_row = 0

    context.chat_data.current_assessment_question_index += 1
    context.chat_data.current_assessment_question_id = context.chat_data.assessment.questions[
        context.chat_data.current_assessment_question_index
    ].id

    await CQReplySender.ask_next_assessment_question(context, query)
    return ConversationState.ASK_ASSESSMENT_QUESTION


async def send_smalltalk_url_or_ask_communication_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If student wants to take SmallTalk test, give them URL. Else, ask communication language."""
    query, data = await answer_callback_query_and_get_data(update)
    locale: Locale = context.user_data.locale

    if data == CommonCallbackData.YES:
        context.user_data.student_agreed_to_smalltalk = True
        context.user_data.student_smalltalk_test_id, url = await send_user_data_get_smalltalk_test(
            first_name=context.user_data.first_name,
            last_name=context.user_data.last_name,
            email=context.user_data.email,
            bot=context.bot,
        )
        await query.edit_message_text(
            context.bot_data.phrases["give_smalltalk_url"][locale]
            + f"\n\n[*{context.bot_data.phrases['give_smalltalk_url_link'][locale]}*]({url})",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            context.bot_data.phrases["answer_smalltalk_done"][locale],
                            callback_data=CommonCallbackData.DONE,
                        )
                    ]
                ]
            ),
        )
        return ConversationState.ASK_COMMUNICATION_LANGUAGE_AFTER_SMALLTALK

    # Without SmallTalk, just take whatever level we got after the "written" assessment
    context.user_data.student_agreed_to_smalltalk = False
    context.user_data.language_and_level_ids = [
        context.bot_data.language_and_level_id_for_language_id_and_level[
            ("en", context.user_data.student_assessment_resulting_level)
        ]
    ]

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationState.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW


async def ask_communication_language_after_smalltalk(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores nothing, just asks about communication language in class."""
    query, _ = await answer_callback_query_and_get_data(update)
    # We will request results from SmallTalk later to increase chance that it's ready.
    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationState.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW
