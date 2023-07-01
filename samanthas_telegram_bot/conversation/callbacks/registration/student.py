from telegram import Update
from telegram.ext import ConversationHandler

from samanthas_telegram_bot.api_clients import BackendClient
from samanthas_telegram_bot.api_clients.smalltalk.exceptions import SmallTalkClientError
from samanthas_telegram_bot.api_clients.smalltalk.smalltalk_client import SmallTalkClient
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationMode,
    ConversationStateCommon,
    ConversationStateStudent,
)
from samanthas_telegram_bot.conversation.auxil.helpers import (
    answer_callback_query_and_get_data,
    notify_speaking_club_coordinator_about_high_level_student,
    prepare_assessment,
    store_selected_language_level,
)
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.conversation.callbacks.registration.exceptions import RegistrationError
from samanthas_telegram_bot.data_structures.constants import (
    ENGLISH,
    LEVELS_ELIGIBLE_FOR_ORAL_TEST,
    LEVELS_TOO_HIGH,
)
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import LoggingLevel
from samanthas_telegram_bot.data_structures.models import AssessmentAnswer


async def store_age_ask_timezone(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores student's age group, asks timezone."""
    query, data = await answer_callback_query_and_get_data(update)
    user_data = context.user_data

    age_range_id = int(data)
    user_data.student_age_range_id = age_range_id
    user_data.student_age_from = context.bot_data.student_ages_for_age_range_id[
        age_range_id
    ].age_from
    user_data.student_age_to = context.bot_data.student_ages_for_age_range_id[age_range_id].age_to

    await logs(
        update=update,
        bot=context.bot,
        text=(
            f"Age group of the student: ID {user_data.student_age_range_id} "
            f"({user_data.student_age_from}-{user_data.student_age_to} years old)"
        ),
    )

    if context.chat_data.mode == ConversationMode.REVIEW:
        await MessageSender.ask_review(update, context)
        return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    # No matter what language the student will choose, we want to prepare assessment-related
    # data as soon as student's age is determined (see rationale in docstring of function below).
    await prepare_assessment(update, context)

    await CQReplySender.ask_timezone(context, query)
    return ConversationStateCommon.TIME_SLOTS_START


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

    * Very young learners are marked as needing an oral interview.
    * Adolescents are asked a question on how long they've been learning.
    * Adults start taking the assessment.
    """
    query, _ = await answer_callback_query_and_get_data(update)
    user_data = context.user_data

    # this callback is called if pattern matches "yes"
    user_data.student_can_read_in_english = True

    await logs(update=update, bot=context.bot, text="User can read in English")

    if user_data.student_age_to <= 12:
        # young students: mark as requiring interview, ask about communication language
        user_data.student_needs_oral_interview = True
        await logs(
            update=update,
            bot=context.bot,
            text="User needs oral interview in English.",
        )
        await CQReplySender.ask_class_communication_languages(context, query)
        return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW
    elif user_data.student_age_to < 18:
        # students of age 13 through 17 are asked how long they have been learning English
        await CQReplySender.ask_how_long_been_learning_english(context, query)
        return ConversationStateStudent.ADOLESCENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_TEST
    else:
        # adult students: start assessment
        await CQReplySender.ask_start_assessment(context, query)
        return ConversationStateStudent.ASK_QUESTION_IN_TEST_OR_GET_RESULTING_LEVEL


async def ask_communication_language_for_students_that_cannot_read_in_english(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """For English learners that cannot read in English: ask communication language.

    * Adult students automatically get "A0"
    * Young students are marked as needing an interview.
    """
    query, _ = await answer_callback_query_and_get_data(update)
    user_data = context.user_data

    # this callback is only called if pattern matches "No"
    user_data.student_can_read_in_english = False

    # Adult students get A0...
    if user_data.student_age_from >= 18:
        user_data.language_and_level_ids = [
            context.bot_data.language_and_level_id_for_language_id_and_level[(ENGLISH, "A0")]
        ]
    else:
        # ...while young students get no level and are marked to require oral interview.
        user_data.student_needs_oral_interview = True
        await logs(
            update=update,
            bot=context.bot,
            text="User needs oral interview in English.",
        )

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

    # Students can only choose one language and one level, so no menu
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

    await logs(
        update=update,
        bot=context.bot,
        text="Adolescent student has learned English for year or more. Starting assessment",
    )
    await CQReplySender.ask_start_assessment(context, query)
    return ConversationStateStudent.ASK_QUESTION_IN_TEST_OR_GET_RESULTING_LEVEL


async def ask_communication_language_for_teen_student_that_learned_less_than_year(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores that teen student needs oral interview (no test). Asks communication language."""
    query, _ = await answer_callback_query_and_get_data(update)

    await logs(
        update=update,
        bot=context.bot,
        text="Student has learned English for less than a year. Will need oral interview",
    )
    context.user_data.student_needs_oral_interview = True

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW


async def assessment_ask_first_question(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Asks first question of the assessment."""
    query, _ = await answer_callback_query_and_get_data(update)

    await CQReplySender.ask_next_assessment_question(context, query)
    return ConversationStateStudent.ASK_QUESTION_IN_TEST_OR_GET_RESULTING_LEVEL


async def get_result_of_aborted_assessment(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Gets result of an assessment if the student has aborted it."""
    next_state = await _process_assessment_results(update, context)
    return next_state


async def store_assessment_answer_ask_next_question_or_get_result_if_finished(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores answer to the question, asks next one. If test is finished, gets result."""
    query, data = await answer_callback_query_and_get_data(update)

    context.user_data.student_assessment_answers.append(
        AssessmentAnswer(
            question_id=context.chat_data.current_assessment_question_id,
            answer_id=int(data),
        )
    )

    # If user has finished the test: get level and exit assessment
    if len(context.user_data.student_assessment_answers) == len(
        context.chat_data.assessment.questions
    ):
        next_state = await _process_assessment_results(update, context)
        return next_state

    if int(data) in context.chat_data.ids_of_dont_know_options_in_assessment:
        await logs(
            update=update,
            bot=context.bot,
            level=LoggingLevel.DEBUG,
            text="User replied 'I don't know'",
        )
        context.chat_data.assessment_dont_knows_in_a_row += 1
    else:
        context.chat_data.assessment_dont_knows_in_a_row = 0

    context.chat_data.current_assessment_question_index += 1
    context.chat_data.current_assessment_question_id = context.chat_data.assessment.questions[
        context.chat_data.current_assessment_question_index
    ].id

    await CQReplySender.ask_next_assessment_question(context, query)
    return ConversationStateStudent.ASK_QUESTION_IN_TEST_OR_GET_RESULTING_LEVEL


async def _process_assessment_results(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Processes results of a written assessment, returns appropriate next conversation state."""
    query, _ = await answer_callback_query_and_get_data(update)

    level = await BackendClient.get_level_after_assessment(update, context)
    context.user_data.student_assessment_resulting_level = level

    if level in LEVELS_ELIGIBLE_FOR_ORAL_TEST:
        await CQReplySender.ask_yes_no(
            context,
            query,
            question_phrase_internal_id="ask_student_start_oral_test",
            parse_mode=None,
        )
        return ConversationStateStudent.SEND_SMALLTALK_URL_OR_ASK_COMMUNICATION_LANGUAGE
    elif level in LEVELS_TOO_HIGH:
        await CQReplySender.ask_yes_no(
            context,
            query,
            question_phrase_internal_id="student_level_too_high_ask",
            parse_mode=None,
        )
        return ConversationStateStudent.ASK_COMMUNICATION_LANGUAGE_OR_BYE
    else:
        # TODO add some compliment on completing the test even without oral test?
        context.user_data.language_and_level_ids = [
            context.bot_data.language_and_level_id_for_language_id_and_level[
                (ENGLISH, context.user_data.student_assessment_resulting_level)
            ]
        ]
        await CQReplySender.ask_class_communication_languages(context, query)
        return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW


async def send_smalltalk_url(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """If student wants SmallTalk test, gives URL. Asks student to press 'Done' when finished."""
    query, data = await answer_callback_query_and_get_data(update)
    user_data = context.user_data

    user_data.student_agreed_to_smalltalk = True
    try:
        (
            user_data.student_smalltalk_test_id,
            user_data.student_smalltalk_interview_url,
        ) = await SmallTalkClient.send_user_data_get_test(update, context)
    except SmallTalkClientError as err:
        raise RegistrationError("Failed to get SmallTalk test") from err
        pass  # TODO notify student, assign level based on written assessment
    await CQReplySender.send_smalltalk_url(context, query)
    return ConversationStateStudent.ASK_COMMUNICATION_LANGUAGE_AFTER_SMALLTALK


async def skip_smalltalk_ask_communication_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Asks the student that wants no oral test about communication language.

    Sets their level of English to whatever they got after the in-bot assessment.
    """
    query, _ = await answer_callback_query_and_get_data(update)
    user_data = context.user_data

    # Without SmallTalk, just take whatever level we got after the "written" assessment
    user_data.student_agreed_to_smalltalk = False
    user_data.language_and_level_ids = [
        context.bot_data.language_and_level_id_for_language_id_and_level[
            (ENGLISH, user_data.student_assessment_resulting_level)
        ]
    ]

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW


async def ask_communication_language_after_smalltalk(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Asks about communication language in class after SmallTalk. No data is stored here."""
    query, _ = await answer_callback_query_and_get_data(update)
    # We will request results from SmallTalk later to increase chance that it's ready.
    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationStateStudent.ASK_NON_TEACHING_HELP_OR_START_REVIEW


async def store_communication_language_ask_non_teaching_help_or_start_review(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores communication language, asks about non-teaching help or starts review.

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
    """Stores one type of non-teaching help student requires, asks another."""
    query, data = await answer_callback_query_and_get_data(update)
    context.user_data.non_teaching_help_types.append(data)

    await CQReplySender.ask_non_teaching_help(context, query)
    return ConversationStateStudent.NON_TEACHING_HELP_MENU_OR_ASK_REVIEW


async def ask_review(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Asks if review is needed."""
    await update.callback_query.answer()
    await MessageSender.ask_review(update, context)
    return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU


async def create_high_level_student(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Special callback for creating students outside common flow.

    It is currently used to create students that after SmallTalk test turn out to be too advanced
    for regular classes and are asked if they want to join speaking club.
    If they agree, they are created in this callback.
    """
    user_data = context.user_data

    person_was_created = await BackendClient.create_student(update, context)

    if person_was_created is True:
        await update.effective_chat.send_message(
            context.bot_data.phrases["student_level_too_high_we_will_email_you"][user_data.locale]
        )
        await notify_speaking_club_coordinator_about_high_level_student(update, context)
    else:
        await logs(
            bot=context.bot,
            text=f"Failed to create student: {user_data=}",
            level=LoggingLevel.CRITICAL,
            needs_to_notify_admin_group=True,
            update=update,
        )

    return ConversationHandler.END
