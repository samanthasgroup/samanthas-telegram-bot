import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.api_client import ApiClient
from samanthas_telegram_bot.api_queries.smalltalk import send_user_data_get_smalltalk_test
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
from samanthas_telegram_bot.conversation.auxil.multi_state_returns import handle_time_slots
from samanthas_telegram_bot.conversation.auxil.prepare_assessment import prepare_assessment
from samanthas_telegram_bot.conversation.auxil.shortcuts import answer_callback_query_and_get_data
from samanthas_telegram_bot.data_structures.constants import (
    LEVELS_ELIGIBLE_FOR_ORAL_TEST,
    NON_TEACHING_HELP_TYPES,
    Locale,
)
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import Role
from samanthas_telegram_bot.data_structures.models import AssessmentAnswer

logger = logging.getLogger(__name__)


async def store_age_ask_slots_for_one_day_or_teaching_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores age group for student, asks timezone.

    * If this function is called for the first time in a conversation, **stores age** and gives
      time slots for Monday.
    * If this function is called after choosing time slots for a day, asks for time slots for the
      next day.
    * If this is the last day, makes asks for the first language to learn/teach.
    """

    query = update.callback_query
    data = query.data

    if not data.isdigit():
        raise NotImplementedError("Only digit-like callback data is accepted here")

    age_range_id = int(data)
    context.user_data.student_age_range_id = age_range_id
    context.user_data.student_age_from = context.bot_data.student_ages_for_age_range_id[
        age_range_id
    ].age_from
    context.user_data.student_age_to = context.bot_data.student_ages_for_age_range_id[
        age_range_id
    ].age_to
    logger.info(
        f"Chat {update.effective_chat.id}. "
        f"Age group of the student: ID {context.user_data.student_age_range_id} "
        f"({context.user_data.student_age_from}-{context.user_data.student_age_to} years old)"
    )
    if context.chat_data.mode == ConversationMode.REVIEW:
        await MessageSender.ask_review(update, context)
        return ConversationStateCommon.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    next_state = await handle_time_slots(update, context)
    return next_state


async def store_teaching_language_ask_another_or_level_or_communication_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores teaching language. Next action depends on language the student wants to learn.

    Stores teaching language.

    If the student selected English, asks for the ability to read in English
    instead of asking for level.

    If the student wants to learn a language other than English, asks for level.
    """

    query, data = await answer_callback_query_and_get_data(update)

    context.user_data.levels_for_teaching_language[data] = []

    # If this is a student that has chosen English, we don't ask them for their level
    # (it will be assessed) - only for their ability to read in English.
    # The question about the ability to read is not asked for languages other than English.
    if context.user_data.role == Role.STUDENT and data == "en":
        await CQReplySender.ask_yes_no(
            context,
            query,
            question_phrase_internal_id="ask_student_if_can_read_in_english",
        )
    else:
        await CQReplySender.ask_language_levels(context, query, show_done_button=False)
    return ConversationStateStudent.ASK_LEVEL_OR_COMMUNICATION_LANGUAGE_OR_START_ASSESSMENT


async def store_data_ask_level_or_communication_language_or_start_assessment(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores data, asks communication language or starts test.

    Stores data:

    * for students that want to learn English, data is their ability to read in English.
    * for students that want to learn other languages or for teachers, data is the level of
      the chosen language.

    Asks:

    * asks students aged 5-12 that want to learn English about communication language, mark that
      they need oral interview
    * asks students aged 13-17 that want to learn English how long they've been learning
    * for adult students that want to learn English, start assessment
    * asks students of other ages that want to learn English about communication language
    * asks students that want to learn other languages about communication language in groups
    """

    query, data = await answer_callback_query_and_get_data(update)

    user_data = context.user_data
    last_language_added = tuple(user_data.levels_for_teaching_language.keys())[-1]

    # If the student had chosen English, query.data is their ability to read in English.
    if last_language_added == "en":
        user_data.student_can_read_in_english = True if data == CommonCallbackData.YES else False

        can_read = user_data.student_can_read_in_english
        logger.info(f"Chat {update.effective_chat.id}. User can read in English: {can_read}")

        if can_read and user_data.student_age_to <= 12:
            # young students: mark as requiring interview, ask about communication language
            user_data.student_needs_oral_interview = True
            await CQReplySender.ask_class_communication_languages(context, query)
            return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW

        if can_read and user_data.student_age_to < 18:
            # students of age 13 through 17 are asked how long they have been learning English
            await CQReplySender.ask_how_long_been_learning_english(context, query)
            return (
                ConversationStateStudent.ADOLESCENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_ASSESSMENT
            )

        if can_read and user_data.student_age_from >= 18:
            # adult students: start assessment
            await prepare_assessment(context, query)
            return ConversationStateStudent.ASK_ASSESSMENT_QUESTION

        # if a student can NOT read in English: no assessment.  Adult students get A0...
        if user_data.student_age_from >= 18:
            user_data.language_and_level_ids = [
                context.bot_data.language_and_level_id_for_language_id_and_level[("en", "A0")]
            ]
        else:
            # ...while young students get no level and are marked to require oral interview.
            user_data.student_needs_oral_interview = True

        if user_data.student_needs_oral_interview:
            logger.info(f"Chat {update.effective_chat.id}. User needs oral interview in English.")

        await CQReplySender.ask_class_communication_languages(context, query)
        return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW

    # If this is a teacher or a student that had chosen another language than English,
    # query.data is language level.
    user_data.levels_for_teaching_language[last_language_added].append(data)
    user_data.language_and_level_ids.append(
        context.bot_data.language_and_level_id_for_language_id_and_level[
            (last_language_added, data)
        ]
    )

    if context.chat_data.mode == ConversationMode.REVIEW:
        await MessageSender.ask_review(update, context)
        return ConversationStateCommon.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    # Students can only choose one language and one level
    await CQReplySender.ask_class_communication_languages(
        context,
        query,
    )
    return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW


async def ask_communication_language_or_start_assessment(
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
        return ConversationStateStudent.ASK_ASSESSMENT_QUESTION

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
        return ConversationStateStudent.ASK_ASSESSMENT_QUESTION

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
    return ConversationStateStudent.ASK_ASSESSMENT_QUESTION


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
        return ConversationStateStudent.NON_TEACHING_HELP_MENU_OR_REVIEW

    await MessageSender.ask_review(update, context)
    return ConversationStateCommon.REVIEW_MENU_OR_ASK_FINAL_COMMENT


async def store_non_teaching_help_ask_another_or_review(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    query, data = await answer_callback_query_and_get_data(update)

    # protection against coding error
    if data not in NON_TEACHING_HELP_TYPES + (CommonCallbackData.DONE,):
        raise ValueError(f"{data} cannot be in callback data for non-teaching help types.")

    # pressed "Done" or chose all types of help
    if data == CommonCallbackData.DONE or len(context.user_data.non_teaching_help_types) == len(
        NON_TEACHING_HELP_TYPES
    ):
        await MessageSender.ask_review(update, context)
        return ConversationStateCommon.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    context.user_data.non_teaching_help_types.append(data)
    await CQReplySender.ask_non_teaching_help(context, query)
    return ConversationStateStudent.NON_TEACHING_HELP_MENU_OR_REVIEW
