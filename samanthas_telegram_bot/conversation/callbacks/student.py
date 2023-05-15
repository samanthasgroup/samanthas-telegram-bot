from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from samanthas_telegram_bot.api_queries import get_smalltalk_url, send_written_answers_get_level
from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.conversation.auxil.prepare_assessment import prepare_assessment
from samanthas_telegram_bot.conversation.auxil.shortcuts import answer_callback_query_and_get_data
from samanthas_telegram_bot.conversation.data_structures.constants import DIGIT_PATTERN, Locale
from samanthas_telegram_bot.conversation.data_structures.context_types import (
    CUSTOM_CONTEXT_TYPES,
    AssessmentAnswer,
)
from samanthas_telegram_bot.conversation.data_structures.enums import (
    CommonCallbackData,
    ConversationState,
)


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
        await prepare_assessment(context, query)
        return ConversationState.ASK_ASSESSMENT_QUESTION

    context.user_data.student_needs_oral_interview = True

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationState.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW


async def assessment_store_answer_ask_question(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores answer to the question (unless this is the beginning of the test), asks next one."""
    query, data = await answer_callback_query_and_get_data(update)

    if (
        context.chat_data.current_assessment_question_index
        == len(context.user_data.student_assessment.questions) - 1
    ):
        level = await send_written_answers_get_level({})  # TODO
        if level == "A2":  # TODO A2 or higher
            await CQReplySender.ask_yes_no(
                context,
                query,
                question_phrase_internal_id="ask_student_start_oral_test",
                parse_mode=None,
            )
            return ConversationState.SEND_SMALLTALK_URL_OR_ASK_COMMUNICATION_LANGUAGE
        else:
            # TODO add some compliment on completing the test even without oral test?
            await CQReplySender.ask_class_communication_languages(context, query)
            return ConversationState.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW

    if DIGIT_PATTERN.match(data):  # this is ID of student's answer
        context.user_data.student_assessment_answers.append(
            AssessmentAnswer(
                question_id=context.chat_data.current_assessment_question_id,
                answer_id=data,
            )
        )
        context.chat_data.current_assessment_question_index += 1
        context.chat_data.current_assessment_question_id = (
            context.user_data.student_assessment.questions[
                context.chat_data.current_assessment_question_index
            ].id
        )

    await CQReplySender.ask_next_assessment_question(context, query)
    return ConversationState.ASK_ASSESSMENT_QUESTION


async def send_smalltalk_url_or_ask_communication_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If student wants to take Smalltalk test, give them URL. Else, ask communication language."""
    query, data = await answer_callback_query_and_get_data(update)
    locale: Locale = context.user_data.locale

    if data == CommonCallbackData.YES:
        url = await get_smalltalk_url(
            first_name=context.user_data.first_name,
            last_name=context.user_data.last_name,
            email=context.user_data.email,
        )
        await query.edit_message_text(
            context.bot_data.phrases["give_smalltalk_url"][locale]
            + f"\n{url}",  # TODO add link onto a text
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

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationState.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW


async def ask_communication_language_after_smalltalk(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores nothing, just asks about communication language in class."""
    query, _ = await answer_callback_query_and_get_data(update)
    # TODO store something in user_data to signal that the user passed the test and that
    #  the backend should try and load results?
    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationState.ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW
