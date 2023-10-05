from telegram import Update

from samanthas_telegram_bot.conversation.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.conversation.auxil.enums import (
    ConversationStateCommon,
    ConversationStateCoordinator,
)
from samanthas_telegram_bot.conversation.auxil.helpers import answer_callback_query_and_get_data
from samanthas_telegram_bot.conversation.auxil.message_sender import MessageSender
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES


async def ask_timezone(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Ask timezone."""

    query, _ = await answer_callback_query_and_get_data(update)
    await CQReplySender.ask_timezone(context, query)
    return ConversationStateCoordinator.ASK_ADDITIONAL_HELP


async def store_timezone_ask_additional_help(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Store timezone, ask for additional help coordinator can provide."""
    user_data = context.user_data

    query, data = await answer_callback_query_and_get_data(update)
    user_data.utc_offset_hour, user_data.utc_offset_minute = (
        int(item) for item in data.split(":")  # TODO this is repetition, but only one line
    )
    await CQReplySender.ask_teacher_or_coordinator_additional_help(context, query)
    return ConversationStateCoordinator.ASK_REVIEW


async def store_additional_help_show_review_menu(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int | None:
    """Store info on additional help, show review menu."""
    message = update.message
    if message is None:
        return None

    context.user_data.volunteer_additional_skills_comment = message.text

    await MessageSender.delete_message_and_ask_review(update, context)
    return ConversationStateCommon.ASK_FINAL_COMMENT_OR_SHOW_REVIEW_MENU
