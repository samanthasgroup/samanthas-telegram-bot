import logging

from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler

from samanthas_telegram_bot.callbacks.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.callbacks.auxil.message_sender import MessageSender
from samanthas_telegram_bot.constants import (
    PHRASES,
    STUDENT_AGE_GROUPS_FOR_TEACHER,
    CallbackData,
    ChatMode,
    Role,
    State,
)
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES

logger = logging.getLogger(__name__)


async def store_readiness_to_host_speaking_clubs_ask_additional_help_or_bye(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If teacher is ready to host speaking clubs, asks for additional skills, else says bye.

    This callback is for young teachers only.
    """
    query = update.callback_query
    await query.answer()
    locale = context.user_data.locale

    await query.delete_message()

    if query.data == CallbackData.YES:  # yes, I can host speaking clubs
        context.user_data.teacher_can_host_speaking_club = True
        await update.effective_chat.send_message(
            PHRASES["ask_teacher_any_additional_help"][locale]
        )
        return State.ASK_FINAL_COMMENT

    await update.effective_chat.send_message(PHRASES["reply_cannot_work"][locale])
    return ConversationHandler.END


async def store_communication_language_ask_teaching_experience(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Callback for teachers. Stores communication language, asks about teaching experience."""

    query = update.callback_query
    await query.answer()

    context.user_data.communication_language_in_class = query.data

    if context.chat_data["mode"] == ChatMode.REVIEW:
        await query.delete_message()
        await MessageSender.ask_review(update, context)
        return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    logger.info(context.user_data.communication_language_in_class)

    await CQReplySender.ask_yes_no(
        context, query, question_phrase_internal_id="ask_teacher_experience"
    )
    return State.ASK_TEACHING_GROUP_OR_SPEAKING_CLUB


async def store_experience_ask_about_groups_or_speaking_clubs(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores if teacher has experience, asks teaching preferences (groups vs speaking clubs)."""

    query = update.callback_query
    await query.answer()

    context.user_data.teacher_has_prior_experience = (
        True if query.data == CallbackData.YES else False
    )

    await CQReplySender.ask_teacher_can_teach_regular_groups_speaking_clubs(context, query)
    return State.ASK_NUMBER_OF_GROUPS_OR_TEACHING_FREQUENCY_OR_NON_TEACHING_HELP


async def store_teaching_preference_ask_groups_or_frequency_or_student_age(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores information about teaching preferences, next action depends on several factors:

    * If teacher only wants to host speaking clubs, asks about preferred student age groups
    * If teacher can teach regular groups but has no experience, asks about frequency
    * If teacher can teach regular groups and has experience, asks about number of groups
    """

    query = update.callback_query
    await query.answer()

    context.user_data.teacher_can_host_speaking_club = (
        True if query.data in ("speaking_club", "both") else False
    )

    if query.data == "speaking_club":  # teacher does not want to teach regular groups
        await CQReplySender.ask_teacher_age_groups_of_students(context, query)
        return State.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP

    if context.user_data.teacher_has_prior_experience is True:
        await CQReplySender.ask_teacher_number_of_groups(context, query)
        return State.ASK_TEACHING_FREQUENCY

    # inexperienced teacher only get one group
    context.user_data.teacher_number_of_groups = 1
    await CQReplySender.ask_teaching_frequency(context, query)
    return State.PREFERRED_STUDENT_AGE_GROUPS_START


async def store_number_of_groups_ask_frequency(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """For experienced teachers: stores information about number of groups, asks for frequency
    (inexperienced teachers).
    """
    query = update.callback_query
    await query.answer()

    context.user_data.teacher_number_of_groups = query.data

    await CQReplySender.ask_teaching_frequency(context, query)
    return State.PREFERRED_STUDENT_AGE_GROUPS_START


async def store_frequency_ask_student_age_groups(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores frequency, asks for preferred age groups of students."""
    query = update.callback_query
    await query.answer()

    context.user_data.teacher_class_frequency = query.data

    await CQReplySender.ask_teacher_age_groups_of_students(context, query)

    return State.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP


async def store_student_age_group_ask_another_or_non_teaching_help(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores preferred age group of students, asks another.  If the teacher is done, ask about
    additional help for students.
    """
    query = update.callback_query
    await query.answer()

    if query.data != CallbackData.DONE:
        context.user_data.teacher_age_groups_of_students.append(query.data)

    # teacher pressed "Done" or chose all age groups
    if query.data == CallbackData.DONE or len(
        context.user_data.teacher_age_groups_of_students
    ) == len(STUDENT_AGE_GROUPS_FOR_TEACHER):
        await CQReplySender.ask_non_teaching_help(context, query)
        return State.NON_TEACHING_HELP_MENU_OR_PEER_HELP_FOR_TEACHER_OR_REVIEW_FOR_STUDENT

    await CQReplySender.ask_teacher_age_groups_of_students(context, query)
    return State.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP


async def store_peer_help_ask_another_or_additional_help(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores one option of teacher peer help, asks for another.  If the teacher is done,
    asks for any additional help (in free text)."""
    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.DONE:
        await query.edit_message_text(
            PHRASES["ask_teacher_any_additional_help"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return State.ASK_REVIEW

    if query.data == "consult":
        context.user_data.teacher_peer_help.can_consult_other_teachers = True
    elif query.data == "children_group":
        context.user_data.teacher_peer_help.can_help_with_children_group = True
    elif query.data == "materials":
        context.user_data.teacher_peer_help.can_help_with_materials = True
    elif query.data == "check_syllabus":
        context.user_data.teacher_peer_help.can_check_syllabus = True
    elif query.data == "feedback":
        context.user_data.teacher_peer_help.can_give_feedback = True
    elif query.data == "invite":
        context.user_data.teacher_peer_help.can_invite_to_class = True
    elif query.data == "tandem":
        context.user_data.teacher_peer_help.can_work_in_tandem = True

    # to remove this button from the keyboard
    context.chat_data["peer_help_callback_data"].add(query.data)
    await CQReplySender.ask_teacher_peer_help(context, query)
    return State.PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP


async def store_teachers_additional_skills_ask_if_review_needed(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores teacher's additional skills and asks to review main user data."""
    if update.message is None:
        return State.ASK_REVIEW

    if context.user_data.role == Role.TEACHER:
        context.user_data.teacher_additional_skills_comment = update.message.text

    await MessageSender.ask_review(update, context)
    return State.REVIEW_MENU_OR_ASK_FINAL_COMMENT
