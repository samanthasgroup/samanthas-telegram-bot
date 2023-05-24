import logging

from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler

from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.conversation.auxil.shortcuts import answer_callback_query_and_get_data
from samanthas_telegram_bot.data_structures.constants import TEACHER_PEER_HELP_TYPES, Locale
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import (
    AgeRangeType,
    CommonCallbackData,
    ConversationMode,
    ConversationState,
    Role,
    TeachingMode,
)

logger = logging.getLogger(__name__)


async def young_teacher_store_readiness_to_host_speaking_clubs_ask_communication_language_or_bye(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If teacher is ready to host speaking clubs, asks for communication language, else says bye.

    This callback is for young teachers only.
    """
    query, data = await answer_callback_query_and_get_data(update)
    locale: Locale = context.user_data.locale

    if data == CommonCallbackData.YES:  # yes, I can host speaking clubs
        context.user_data.teacher_can_host_speaking_club = True
        await CQReplySender.ask_class_communication_languages(context, query)
        return ConversationState.ASK_YOUNG_TEACHER_SPEAKING_CLUB_LANGUAGE

    await update.effective_chat.send_message(context.bot_data.phrases["reply_cannot_work"][locale])
    return ConversationHandler.END


async def young_teacher_store_communication_language_ask_speaking_club_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores communication language, asks language of speaking clubs they want to host.

    This callback is for young teachers only.
    """
    query, data = await answer_callback_query_and_get_data(update)
    context.user_data.communication_language_in_class = data

    await CQReplySender.ask_teaching_languages(context, query, show_done_button=False)
    return ConversationState.ASK_YOUNG_TEACHER_ADDITIONAL_HELP


async def young_teacher_store_teaching_language_ask_additional_help(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores teaching language, asks additional skills."""
    query, lang_id = await answer_callback_query_and_get_data(update)
    await query.delete_message()

    logger.info(
        f"Chat {update.effective_chat.id}. Young teacher wants to host speaking clubs in {lang_id}"
    )

    # TODO this is a temporary measure to keep things simple as there are very few young teachers.
    #  For now we just say that a young teacher who wants to host speaking club only chooses
    #  one single language and we automatically add pre-intermediate level to it (one cannot choose
    #  level higher than A2 for any language other than English).
    #  Maybe we will need to add some more logic, but maybe not.  Speaking clubs are informal.
    context.user_data.language_and_level_ids = [
        context.bot_data.language_and_level_id_for_language_id_and_level[(lang_id, "A2")]
    ]

    await update.effective_chat.send_message(
        context.bot_data.phrases["ask_teacher_any_additional_help"][context.user_data.locale]
    )
    return ConversationState.ASK_FINAL_COMMENT


async def store_communication_language_ask_teaching_experience(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Callback for teachers. Stores communication language, asks about teaching experience."""

    (
        query,
        context.user_data.communication_language_in_class,
    ) = await answer_callback_query_and_get_data(update)

    if context.chat_data.mode == ConversationMode.REVIEW:
        await query.delete_message()
        await MessageSender.ask_review(update, context)
        return ConversationState.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    await CQReplySender.ask_yes_no(
        context, query, question_phrase_internal_id="ask_teacher_experience"
    )
    return ConversationState.ASK_TEACHING_GROUP_OR_SPEAKING_CLUB


async def store_experience_ask_about_groups_or_speaking_clubs(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores if teacher has experience, asks teaching preferences (groups vs speaking clubs)."""

    query, data = await answer_callback_query_and_get_data(update)

    context.user_data.teacher_has_prior_experience = data == CommonCallbackData.YES

    await CQReplySender.ask_teacher_can_teach_regular_groups_speaking_clubs(context, query)
    return ConversationState.ASK_NUMBER_OF_GROUPS_OR_TEACHING_FREQUENCY_OR_NON_TEACHING_HELP


async def store_teaching_preference_ask_groups_or_frequency_or_student_age(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores information about teaching preferences, next action depends on several factors:

    * If teacher only wants to host speaking clubs, asks about preferred student age groups
    * If teacher can teach regular groups but has no experience, asks about frequency
    * If teacher can teach regular groups and has experience, asks about number of groups
    """

    query, data = await answer_callback_query_and_get_data(update)

    context.user_data.teacher_can_host_speaking_club = data in (
        TeachingMode.SPEAKING_CLUB_ONLY,
        TeachingMode.BOTH,
    )

    if data == TeachingMode.SPEAKING_CLUB_ONLY:
        context.user_data.teacher_number_of_groups = 0
        await CQReplySender.ask_teacher_age_groups_of_students(context, query)
        return ConversationState.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP

    if context.user_data.teacher_has_prior_experience is True:
        await CQReplySender.ask_teacher_number_of_groups(context, query)
        return ConversationState.ASK_TEACHING_FREQUENCY

    # inexperienced teacher only get one group
    context.user_data.teacher_number_of_groups = 1
    await CQReplySender.ask_teaching_frequency(context, query)
    return ConversationState.PREFERRED_STUDENT_AGE_GROUPS_START


async def store_number_of_groups_ask_frequency(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """For experienced teachers: stores information about number of groups, asks for frequency
    (inexperienced teachers).
    """
    query, context.user_data.teacher_number_of_groups = await answer_callback_query_and_get_data(
        update
    )

    await CQReplySender.ask_teaching_frequency(context, query)
    return ConversationState.PREFERRED_STUDENT_AGE_GROUPS_START


async def store_frequency_ask_student_age_groups(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores frequency, asks for preferred age groups of students."""
    query, context.user_data.teacher_class_frequency = await answer_callback_query_and_get_data(
        update
    )

    await CQReplySender.ask_teacher_age_groups_of_students(context, query)

    return ConversationState.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP


async def store_student_age_group_ask_another_or_non_teaching_help(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores preferred age group of students, asks another.  If the teacher is done, ask about
    additional help for students.
    """
    query, data = await answer_callback_query_and_get_data(update)

    if data != CommonCallbackData.DONE:
        context.user_data.teacher_student_age_range_ids.append(int(data))

    # teacher pressed "Done" or chose all age groups
    if data == CommonCallbackData.DONE or len(
        context.user_data.teacher_student_age_range_ids
    ) == len(context.bot_data.age_ranges_for_type[AgeRangeType.TEACHER]):
        logger.info(
            f"Chat {update.effective_chat.id}. IDs of student ages "
            f"{context.user_data.teacher_student_age_range_ids}"
        )
        await CQReplySender.ask_non_teaching_help(context, query)
        return (
            ConversationState.NON_TEACHING_HELP_MENU_OR_PEER_HELP_FOR_TEACHER_OR_REVIEW_FOR_STUDENT
        )

    await CQReplySender.ask_teacher_age_groups_of_students(context, query)
    return ConversationState.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP


async def store_peer_help_ask_another_or_additional_help(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores one option of teacher peer help, asks for another.  If the teacher is done,
    asks for any additional help (in free text)."""
    query, data = await answer_callback_query_and_get_data(update)

    if data == CommonCallbackData.DONE:
        selected_types = ", ".join(
            help_type
            for help_type in TEACHER_PEER_HELP_TYPES
            if getattr(context.user_data.teacher_peer_help, help_type) is True
        )
        logger.info(f"Chat {update.effective_chat.id}: teacher's peer help: {selected_types}")

        await query.edit_message_text(
            context.bot_data.phrases["ask_teacher_any_additional_help"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return ConversationState.ASK_REVIEW

    setattr(context.user_data.teacher_peer_help, data, True)

    # to remove this button from the keyboard
    context.chat_data.peer_help_callback_data.add(data)
    await CQReplySender.ask_teacher_peer_help(context, query)
    return ConversationState.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP


async def store_teachers_additional_skills_ask_if_review_needed(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores teacher's additional skills and asks to review main user data."""
    if update.message is None:
        return ConversationState.ASK_REVIEW

    if context.user_data.role == Role.TEACHER:
        context.user_data.teacher_additional_skills_comment = update.message.text

    await MessageSender.ask_review(update, context)
    return ConversationState.REVIEW_MENU_OR_ASK_FINAL_COMMENT