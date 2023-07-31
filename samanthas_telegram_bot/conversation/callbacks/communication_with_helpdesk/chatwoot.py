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
    bot_data = context.bot_data
    if update.direction == ChatwootMessageDirection.FROM_CHATWOOT_TO_BOT:
        chat_id = int(update.chat_id)  # Telegram updates will have chat IDs as integers!

        await logs(
            bot=context.bot,
            text=f"Received message to be forwarded from Chatwoot to user in chat {chat_id}",
        )  # FIXME debug level

        await context.bot.send_message(chat_id=chat_id, text=update.message, parse_mode=None)
        bot_data.conversation_mode_for_chat_id[
            chat_id
        ] = ConversationMode.COMMUNICATION_WITH_HELPDESK
        await logs(
            bot=context.bot,
            text=(
                f"Mode of chat {chat_id} ({type(chat_id)}) after sending message to user: "
                f"{bot_data.conversation_mode_for_chat_id[chat_id]}"
            ),
        )  # FIXME debug level


async def forward_message_from_user_to_chatwoot(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> None:
    """Forwards message sent by coordinator in Chatwoot to user if communication mode is right."""
    # TODO if this works, try and remove call to forward_message... from fallback.
    if (
        context.bot_data.conversation_mode_for_chat_id[context.user_data.chat_id]
        != ConversationMode.COMMUNICATION_WITH_HELPDESK
    ):
        # await context.application.update_queue.put(update)
        # TODO maybe use a custom filter instead?
        return

    await logs(
        bot=context.bot,
        text=(
            f"Received message to be forwarded from user to Chatwoot. {context.user_data=}, "
            f"{context.chat_data=}, {context.bot_data=}"
        ),
    )  # FIXME debug level

    # FIXME if user sends message after bot restart, there will be an error

    await ChatwootClient.send_message_to_conversation(update, context, update.message.text)
