"""Module for review callbacks.

Each callback returns the state of the conversation that comes right *after* the moment
when the corresponding question was asked in normal conversation flow.

Since chat is supposed to be in review mode by now, the user will return straight back
to review menu after they give amended information "upstream" in the conversation.
"""
import logging

from telegram import InlineKeyboardMarkup, Update

from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.enums import ConversationStateCommon as CommonState
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationStateTeacherAdult as TeacherState,
)
from samanthas_telegram_bot.conversation.auxil.helpers import answer_callback_query_and_get_data
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import Role

logger = logging.getLogger(__name__)


async def first_name(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    query, _ = await answer_callback_query_and_get_data(update)

    await query.edit_message_text(
        context.bot_data.phrases["ask_first_name"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return CommonState.ASK_LAST_NAME


async def last_name(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    query, _ = await answer_callback_query_and_get_data(update)

    await query.edit_message_text(
        context.bot_data.phrases["ask_last_name"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return CommonState.ASK_SOURCE


async def phone(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    await update.effective_message.delete()
    await MessageSender.ask_phone_number(update, context)
    return CommonState.ASK_EMAIL


async def email(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    query, _ = await answer_callback_query_and_get_data(update)

    await query.edit_message_text(
        context.bot_data.phrases["ask_email"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return CommonState.ASK_AGE_OR_BYE_IF_PERSON_EXISTS


async def timezone(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    query, _ = await answer_callback_query_and_get_data(update)

    await CQReplySender.ask_timezone(context, query)
    return CommonState.TIME_SLOTS_START


async def day_and_time_slots(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    query, _ = await answer_callback_query_and_get_data(update)
    context.user_data.day_and_time_slot_ids = []

    await CQReplySender.ask_time_slot(context, query)
    return CommonState.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE


async def languages_and_levels(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    query, _ = await answer_callback_query_and_get_data(update)
    context.user_data.levels_for_teaching_language = {}
    context.user_data.language_and_level_ids = []

    await CQReplySender.ask_teaching_languages(context, query, show_done_button=False)
    return TeacherState.ASK_LEVEL_OR_ANOTHER_LANGUAGE_OR_COMMUNICATION_LANGUAGE


async def class_communication_language(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    query, _ = await answer_callback_query_and_get_data(update)

    await CQReplySender.ask_class_communication_languages(context, query)
    return TeacherState.ASK_TEACHING_EXPERIENCE


async def student_age_groups(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    query, _ = await answer_callback_query_and_get_data(update)

    if context.user_data.role == Role.STUDENT:
        await CQReplySender.ask_student_age_group(context, query)
        return CommonState.ASK_TIMEZONE_OR_IS_YOUNG_TEACHER_READY_TO_HOST_SPEAKING_CLUB

    # TODO is it in the menu?
    await CQReplySender.ask_teacher_age_groups_of_students(context, query)
    return TeacherState.PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP
