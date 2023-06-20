import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.api_client import ApiClient
from samanthas_telegram_bot.api_queries.auxil.enums import LoggingLevel
from samanthas_telegram_bot.api_queries.smalltalk import send_user_data_get_smalltalk_test
from samanthas_telegram_bot.auxil.log_and_notify import log_and_notify
from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    CommonCallbackData,
    ConversationMode,
    ConversationStateCommon,
    ConversationStateStudent,
)
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.conversation.auxil.prepare_assessment import prepare_assessment
from samanthas_telegram_bot.conversation.auxil.shortcuts import (
    answer_callback_query_and_get_data,
    store_selected_language_level,
)
from samanthas_telegram_bot.data_structures.constants import LEVELS_ELIGIBLE_FOR_ORAL_TEST, Locale
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.models import AssessmentAnswer

logger = logging.getLogger(__name__)


async def store_age_ask_slots_for_monday(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores age group for student, asks time slots for Monday."""

    query = update.callback_query
    data = query.data

    user_data = context.user_data

    age_range_id = int(data)
    user_data.student_age_range_id = age_range_id
    user_data.student_age_from = context.bot_data.student_ages_for_age_range_id[
        age_range_id
    ].age_from
    user_data.student_age_to = context.bot_data.student_ages_for_age_range_id[age_range_id].age_to
    await log_and_notify(
        bot=context.bot,
        logger=logger,
        level=LoggingLevel.INFO,
        text=(
            f"Age group of the student: ID {user_data.student_age_range_id} "
            f"({user_data.student_age_from}-{user_data.student_age_to} years old)"
        ),
        needs_to_notify_admin_group=False,
    )

    if context.chat_data.mode == ConversationMode.REVIEW:
        await MessageSender.ask_review(update, context)
        return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await CQReplySender.ask_time_slot(context, query)
    return ConversationStateCommon.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE


async def ask_if_can_read_in_english(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """If student selected English, asks about ability to read in English."""
    query, language_code = await answer_callback_query_and_get_data(update)
    # this might not be needed for English, but keeping the structure uniform
    context.user_data.levels_for_teaching_language[language_code] = []

    await CQReplySender.ask_yes_no(
        context=context,
        query=query,
        question_phrase_internal_id="ask_student_if_can_read_in_english",
    )
    return (
        ConversationStateStudent.ENGLISH_STUDENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_TEST_DEPENDING_ON_ABILITY_TO_READ
    )


async def store_teaching_language_ask_level(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores teaching language (not English). Asks for level."""

    query, language_code = await answer_callback_query_and_get_data(update)

    context.user_data.levels_for_teaching_language[language_code] = []

    await CQReplySender.ask_language_level(context, query, show_done_button=False)
    return ConversationStateStudent.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE_OR_START_TEST


async def ask_or_start_assessment_for_english_reader_depending_on_age(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Callback for English learners that can read in English.

    Very young learners are marked as needing an oral interview.
    Adolescents are asked a question on how long they've been learning.
    Adults start taking the assessment.
    """
    query, _ = await answer_callback_query_and_get_data(update)
    user_data = context.user_data

    # this callback is called if pattern matches "yes"
    user_data.student_can_read_in_english = True

    logger.info(f"Chat {update.effective_chat.id}. User can read in English.")

    if user_data.student_age_to <= 12:
        # young students: mark as requiring interview, ask about communication language
        user_data.student_needs_oral_interview = True
        logger.info(f"Chat {update.effective_chat.id}. User needs oral interview in English.")
        await CQReplySender.ask_class_communication_languages(context, query)
        return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW
    elif user_data.student_age_to < 18:
        # students of age 13 through 17 are asked how long they have been learning English
        await CQReplySender.ask_how_long_been_learning_english(context, query)
        return ConversationStateStudent.ADOLESCENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_TEST
    else:
        # adult students: start assessment
        await prepare_assessment(context, query)
        return ConversationStateStudent.ASK_QUESTION_IN_TEST


async def ask_communication_language_for_students_that_cannot_read_in_english(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """For English learners that cannot read in English: ask communication language.

    Adult students automatically get "A0", young students are marked as needing an interview.
    """
    query, _ = await answer_callback_query_and_get_data(update)
    user_data = context.user_data

    # this callback is only called if pattern matches "No"
    user_data.student_can_read_in_english = False

    logger.info(f"Chat {update.effective_chat.id}. User cannot read in English")

    # Adult students get A0...
    if user_data.student_age_from >= 18:
        user_data.language_and_level_ids = [
            context.bot_data.language_and_level_id_for_language_id_and_level[("en", "A0")]
        ]
    else:
        # ...while young students get no level and are marked to require oral interview.
        user_data.student_needs_oral_interview = True
        logger.info(f"Chat {update.effective_chat.id}. User needs oral interview in English.")

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW


async def store_non_english_level_ask_communication_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores level (only for languages other than 'en'), asks communication language."""

    query, language_level = await answer_callback_query_and_get_data(update)
    store_selected_language_level(context=context, level=language_level)

    if context.chat_data.mode == ConversationMode.REVIEW:
        await MessageSender.ask_review(update, context)
        return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    # Students can only choose one language and one level
    await CQReplySender.ask_class_communication_languages(
        context,
        query,
    )
    return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW


async def start_assessment_for_teen_student_that_learned_for_year_or_more(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Starts assessment for young students that have been learning English for a year or more."""
    query, _ = await answer_callback_query_and_get_data(update)

    logger.info(
        f"Chat {update.effective_chat.id}. "
        f"Adolescent student has learned English for year or more. Starting assessment"
    )
    await prepare_assessment(context, query)
    return ConversationStateStudent.ASK_QUESTION_IN_TEST


async def ask_communication_language_for_teen_student_that_learned_less_than_year(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores adolescent student needs oral interview (no test). Asks communication language."""
    query, _ = await answer_callback_query_and_get_data(update)

    logger.info(
        f"Chat {update.effective_chat.id}. "
        f"Student has learned English for less than a year. Will need oral interview"
    )
    context.user_data.student_needs_oral_interview = True

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW


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
        return ConversationStateStudent.ASK_QUESTION_IN_TEST

    # get level if user has finished or aborted the test
    if (
        len(context.user_data.student_assessment_answers)
        == len(context.chat_data.assessment.questions)
    ) or data == CommonCallbackData.ABORT:
        context.user_data.student_assessment_resulting_level = (
            await ApiClient.get_level_of_written_test(context=context)
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
    return ConversationStateStudent.ASK_QUESTION_IN_TEST


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
            context=context,
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
        return ConversationStateStudent.ASK_COMMUNICATION_LANGUAGE_AFTER_SMALLTALK

    # Without SmallTalk, just take whatever level we got after the "written" assessment
    context.user_data.student_agreed_to_smalltalk = False
    context.user_data.language_and_level_ids = [
        context.bot_data.language_and_level_id_for_language_id_and_level[
            ("en", context.user_data.student_assessment_resulting_level)
        ]
    ]

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW


async def ask_communication_language_after_smalltalk(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores nothing, just asks about communication language in class."""
    query, _ = await answer_callback_query_and_get_data(update)
    # We will request results from SmallTalk later to increase chance that it's ready.
    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW


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
        return ConversationStateStudent.NON_TEACHING_HELP_MENU_OR_ASK_REVIEW

    await MessageSender.ask_review(update, context)
    return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU


async def store_non_teaching_help_ask_another(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores one type of non-teaching help student requires, asks another"""
    query, data = await answer_callback_query_and_get_data(update)
    context.user_data.non_teaching_help_types.append(data)

    await CQReplySender.ask_non_teaching_help(context, query)
    return ConversationStateStudent.NON_TEACHING_HELP_MENU_OR_ASK_REVIEW


async def ask_review(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    await update.callback_query.answer()
    await MessageSender.ask_review(update, context)
    return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU
