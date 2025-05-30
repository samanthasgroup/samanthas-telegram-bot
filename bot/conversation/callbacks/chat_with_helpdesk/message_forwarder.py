import os

from telegram import Update

from bot.api_clients import ChatwootClient
from bot.auxil.log_and_notify import logs
from bot.conversation.auxil.enums import ConversationMode
from bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from bot.data_structures.custom_updates import ChatwootMessageDirection, ChatwootUpdate
from bot.data_structures.enums import LoggingLevel

CHATWOOT_DISABLED = os.environ.get("CHATWOOT_DISABLED", "true").lower() == "true"


class MessageForwarder:
    """Class for forwarding messages from helpdesk to user in bot and vice versa."""

    @staticmethod
    async def from_helpdesk_to_user(update: ChatwootUpdate, context: CUSTOM_CONTEXT_TYPES) -> None:
        if CHATWOOT_DISABLED:
            return
        """Forward message sent by coordinator to user, switch communication mode."""
        bot_data = context.bot_data
        if update.direction == ChatwootMessageDirection.FROM_CHATWOOT_TO_BOT:
            chat_id = int(update.chat_id)  # Telegram updates will have chat IDs as integers!

            await logs(
                bot=context.bot,
                level=LoggingLevel.DEBUG,
                text=f"Received message to be forwarded from helpdesk to user in chat {chat_id}",
            )

            await context.bot.send_message(chat_id=chat_id, text=update.message, parse_mode=None)
            bot_data.conversation_mode_for_chat_id[chat_id] = (
                ConversationMode.COMMUNICATION_WITH_HELPDESK
            )

            await logs(
                bot=context.bot,
                level=LoggingLevel.DEBUG,
                text=(
                    f"Mode of chat {chat_id} ({type(chat_id)}) after sending message to user: "
                    f"{bot_data.conversation_mode_for_chat_id[chat_id]}"
                ),
            )

    @staticmethod
    async def from_user_to_helpdesk(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
        if CHATWOOT_DISABLED:
            return
        """Forward message sent by user to coordinator in helpdesk."""

        await logs(
            bot=context.bot,
            level=LoggingLevel.DEBUG,
            text=(
                f"Received message to be forwarded from user to helpdesk. {context.user_data=}, "
                f"{context.chat_data=}, {context.bot_data=}"
            ),
        )

        await ChatwootClient.send_message_to_conversation(update, context, update.message.text)
