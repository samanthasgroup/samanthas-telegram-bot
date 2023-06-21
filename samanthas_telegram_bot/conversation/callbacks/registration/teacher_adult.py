import logging

from telegram import Update

from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    CommonCallbackData,
    ConversationMode,
    ConversationStateCommon,
    ConversationStateTeacherAdult,
)
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.conversation.auxil.shortcuts import (
    answer_callback_query_and_get_data,
    store_selected_language_level,
)
from samanthas_telegram_bot.data_structures.constants import TEACHER_PEER_HELP_TYPES
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import TeachingMode

logger = logging.getLogger(__name__)


async def ask_timezone(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Ask timezone."""

    query, _ = await answer_callback_query_and_get_data(update)
    # this callback is only called if the teacher is an adult
    context.user_data.teacher_is_under_18 = False

    await CQReplySender.ask_timezone(context, query)
    return ConversationStateCommon.TIME_SLOTS_START


async def store_teaching_language_ask_level(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores teaching language, asks level."""

    query, language_code = await answer_callback_query_and_get_data(update)
    context.user_data.levels_for_teaching_language[language_code] = []

    await CQReplySender.ask_language_level(context, query, show_done_button=False)
    return ConversationStateTeacherAdult.ASK_LEVEL_OR_ANOTHER_LANGUAGE_OR_COMMUNICATION_LANGUAGE


async def store_level_ask_another(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores level of teaching language, asks to choose another level."""
    query, language_level = await answer_callback_query_and_get_data(update)
    store_selected_language_level(context=context, level=language_level)

    await CQReplySender.ask_language_level(context, query, show_done_button=True)
    return ConversationStateTeacherAdult.ASK_LEVEL_OR_ANOTHER_LANGUAGE_OR_COMMUNICATION_LANGUAGE


async def ask_next_teaching_language(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Asks for next teaching language."""
    query, _ = await answer_callback_query_and_get_data(update)

    await CQReplySender.ask_teaching_languages(context, query, show_done_button=True)
    return ConversationStateTeacherAdult.ASK_LEVEL_OR_ANOTHER_LANGUAGE_OR_COMMUNICATION_LANGUAGE


async def ask_class_communication_language(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Asks for communication language in class. No data is stored here."""
    query, _ = await answer_callback_query_and_get_data(update)

    logger.info(
        f"Chat {update.effective_chat.id}. Selected teaching language(s) and level(s): "
        f"{context.user_data.levels_for_teaching_language} "
        f"(IDs: {context.user_data.language_and_level_ids})"
    )

    if context.chat_data.mode == ConversationMode.REVIEW:
        await query.delete_message()
        await MessageSender.ask_review(update, context)  # TODO do the same thing in CQReplySender?
        return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await CQReplySender.ask_class_communication_languages(context, query)
    return ConversationStateTeacherAdult.ASK_TEACHING_EXPERIENCE


async def store_communication_language_ask_teaching_experience(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores communication language, asks about teaching experience."""

    (
        query,
        context.user_data.communication_language_in_class,
    ) = await answer_callback_query_and_get_data(update)

    if context.chat_data.mode == ConversationMode.REVIEW:
        await query.delete_message()
        await MessageSender.ask_review(update, context)
        return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await CQReplySender.ask_yes_no(
        context, query, question_phrase_internal_id="ask_teacher_experience"
    )
    return ConversationStateTeacherAdult.ASK_TEACHING_GROUP_OR_SPEAKING_CLUB


async def store_experience_ask_teaching_groups_vs_hosting_speaking_clubs(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores if teacher has experience, asks teaching preferences (groups vs speaking clubs)."""

    query, data = await answer_callback_query_and_get_data(update)
    context.user_data.teacher_has_prior_experience = data == CommonCallbackData.YES

    await CQReplySender.ask_teacher_can_teach_regular_groups_speaking_clubs(context, query)
    return ConversationStateTeacherAdult.ASK_NUMBER_OF_GROUPS_OR_FREQUENCY_OR_NON_TEACHING_HELP


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
        return (
            ConversationStateTeacherAdult.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP
        )

    if context.user_data.teacher_has_prior_experience is True:
        await CQReplySender.ask_teacher_number_of_groups(context, query)
        return ConversationStateTeacherAdult.ASK_TEACHING_FREQUENCY

    # inexperienced teacher only get one group
    context.user_data.teacher_number_of_groups = 1
    await CQReplySender.ask_teaching_frequency(context, query)
    return ConversationStateTeacherAdult.PREFERRED_STUDENT_AGE_GROUPS_START


async def store_number_of_groups_ask_frequency(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """For experienced teachers: stores number of groups, asks for frequency."""
    query, context.user_data.teacher_number_of_groups = await answer_callback_query_and_get_data(
        update
    )

    await CQReplySender.ask_teaching_frequency(context, query)
    return ConversationStateTeacherAdult.PREFERRED_STUDENT_AGE_GROUPS_START


async def store_frequency_ask_student_age_groups(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores frequency, asks for preferred age groups of students."""
    query, context.user_data.teacher_class_frequency = await answer_callback_query_and_get_data(
        update
    )

    await CQReplySender.ask_teacher_age_groups_of_students(context, query)
    return ConversationStateTeacherAdult.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP


async def store_student_age_group_ask_another(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores preferred age group of students, asks another."""
    query, data = await answer_callback_query_and_get_data(update)
    context.user_data.teacher_student_age_range_ids.append(int(data))

    await CQReplySender.ask_teacher_age_groups_of_students(context, query)
    return ConversationStateTeacherAdult.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP


async def ask_non_teaching_help(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Asks the teacher for non-teaching help they can provide to the students."""
    query, _ = await answer_callback_query_and_get_data(update)

    logger.info(
        f"Chat {update.effective_chat.id}. IDs of student ages "
        f"{context.user_data.teacher_student_age_range_ids}"
    )
    if context.chat_data.mode == ConversationMode.REVIEW:
        await query.delete_message()
        await MessageSender.ask_review(update, context)
        return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU

    await CQReplySender.ask_non_teaching_help(context, query)
    return ConversationStateTeacherAdult.NON_TEACHING_HELP_MENU_OR_ASK_PEER_HELP_OR_ADDITIONAL_HELP


async def store_non_teaching_help_ask_another(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores one type of non-teaching help teacher can provide, asks another."""
    query, data = await answer_callback_query_and_get_data(update)
    context.user_data.non_teaching_help_types.append(data)

    await CQReplySender.ask_non_teaching_help(context, query)
    return ConversationStateTeacherAdult.NON_TEACHING_HELP_MENU_OR_ASK_PEER_HELP_OR_ADDITIONAL_HELP


async def ask_peer_help_or_additional_help(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Depending on whether the teacher has experience, ask for peer help or additional help."""
    query, _ = await answer_callback_query_and_get_data(update)

    if context.user_data.teacher_has_prior_experience:
        await CQReplySender.ask_teacher_peer_help(context, query)
        return ConversationStateTeacherAdult.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP

    await CQReplySender.ask_teacher_additional_help(context, query)
    return ConversationStateTeacherAdult.ASK_REVIEW


async def store_peer_help_ask_another(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores one option of teacher peer help, asks for another."""
    query, type_of_peer_help = await answer_callback_query_and_get_data(update)

    setattr(context.user_data.teacher_peer_help, type_of_peer_help, True)
    context.chat_data.peer_help_callback_data.add(type_of_peer_help)

    await CQReplySender.ask_teacher_peer_help(context, query)
    return ConversationStateTeacherAdult.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP


async def ask_additional_skills_comment(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Asks for any additional skills (in free text)."""
    query, data = await answer_callback_query_and_get_data(update)
    user_data = context.user_data

    selected_types = ", ".join(
        help_type
        for help_type in TEACHER_PEER_HELP_TYPES
        if getattr(user_data.teacher_peer_help, help_type) is True
    )
    logger.info(f"Chat {update.effective_chat.id}: teacher's peer help: {selected_types}")

    await CQReplySender.ask_teacher_additional_help(context, query)
    return ConversationStateTeacherAdult.ASK_REVIEW


async def store_additional_skills_comment_ask_review(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores teacher's comment on additional skills and asks to review main user data."""
    if update.message is None:
        return ConversationStateTeacherAdult.ASK_REVIEW

    context.user_data.teacher_additional_skills_comment = update.message.text

    await MessageSender.ask_review(update, context)
    return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU
