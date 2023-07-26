from telegram import Update

from samanthas_telegram_bot.api_clients.chatwoot.client import ChatwootClient
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.conversation.auxil.enums import ConversationMode
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.custom_updates import (
    ChatwootMessageDirection,
    ChatwootUpdate,
)


async def forward_message_from_chatwoot_to_user(
    update: ChatwootUpdate, context: CUSTOM_CONTEXT_TYPES
) -> None:
    """Forwards message sent by coordinator in Chatwoot to user, switches communication mode."""
    await logs(
        bot=context.bot, text=f"{context.user_data=}, {context.chat_data=}, {context.bot_data=}"
    )  # FIXME debug level
    if update.direction == ChatwootMessageDirection.FROM_CHATWOOT_TO_BOT:
        await context.bot.send_message(
            chat_id=update.bot_chat_id, text=update.message, parse_mode=None
        )
        context.chat_data.mode = ConversationMode.COMMUNICATION_WITH_HELPDESK


async def forward_message_from_user_to_chatwoot(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> None:
    """Forwards message sent by coordinator in Chatwoot to user, switches communication mode."""
    if context.chat_data.mode == ConversationMode.COMMUNICATION_WITH_HELPDESK:
        await ChatwootClient.send_message_to_conversation(update, context, update.message.text)
