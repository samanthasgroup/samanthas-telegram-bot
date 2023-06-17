"""Module with auxiliary functions that handle callback data and return appropriate
conversation states in 'bifurcation points', e.g. points in conversation where callback data
and reply depend on some characteristics of the user."""
import logging

from telegram import Update

from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    CommonCallbackData,
    ConversationMode,
    ConversationStateCommon,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationStateStudent as StudentState,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationStateTeacher as TeacherState,
)
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import Role

logger = logging.getLogger(__name__)


async def handle_time_slots(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Handles query for time slots and returns appropriate conversation state"""
    # not using a shortcut here because we may need to answer the query with an alert
    query = update.callback_query
    data = query.data

    # If this is a user choosing time slots that has just chosen one time slot
    if data != CommonCallbackData.NEXT:
        await query.answer()
        await CQReplySender.ask_time_slot(context, query)
        return get_state_for_time_slots_menu(context.user_data.role)

    # If this is a user choosing time slots that pressed "next" button after choosing slots...
    if context.chat_data.day_index < 6:  # ...but we haven't yet reached Sunday
        context.chat_data.day_index += 1
        await query.answer()
        await CQReplySender.ask_time_slot(context, query)
        return get_state_for_time_slots_menu(context.user_data.role)

    # ...or if we have reached Sunday
    slots_for_logging = (
        context.bot_data.day_and_time_slot_for_slot_id[slot_id]
        for slot_id in sorted(context.user_data.day_and_time_slot_ids)
    )
    logger.info(
        f"Chat {update.effective_chat.id}. "
        f"Slots: {', '.join(str(slot) for slot in slots_for_logging)}",
        stacklevel=2,  # TODO see if it works
    )

    # reset day of week to Monday for possible review
    context.chat_data.day_index = 0

    if not any(context.user_data.day_and_time_slot_ids):
        await query.answer(
            context.bot_data.phrases["no_slots_selected"][context.user_data.locale],
            show_alert=True,
        )
        logger.info(
            f"Chat {update.effective_chat.id}. User has selected no slots at all",
            stacklevel=2,  # TODO see if it works
        )
        context.chat_data.day_index = 0
        await CQReplySender.ask_time_slot(context, query)
        return get_state_for_time_slots_menu(context.user_data.role)

    if context.chat_data.mode == ConversationMode.REVIEW:
        await query.answer()
        await MessageSender.ask_review(update, context)
        return ConversationStateCommon.REVIEW_MENU_OR_ASK_FINAL_COMMENT

    # if the dictionary is empty, it means that no language was chosen yet.
    # In this case no "done" button must be shown.
    show_done_button = True if context.user_data.levels_for_teaching_language else False
    await query.answer()
    await CQReplySender.ask_teaching_languages(context, query, show_done_button=show_done_button)
    return TeacherState.ASK_LEVEL_OR_ANOTHER_LANGUAGE_OR_COMMUNICATION_LANGUAGE


def get_state_for_time_slots_menu(role: Role) -> int:
    """Returns correct next state for menu of time slots, depending on user's role."""
    match role:
        case Role.STUDENT:
            return StudentState.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE
        case Role.TEACHER:
            return TeacherState.TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE
        case _:
            raise NotImplementedError(f"{role=} not supported")
