from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.custom_updates import ChatwootUpdate


async def forward_message_from_chatwoot_to_user(
    update: ChatwootUpdate, context: CUSTOM_CONTEXT_TYPES
) -> None:
    """Callback that forwards messages sent by coordinator in Chatwoot to the user."""
    await context.bot.send_message(
        chat_id=context.user_data.chat_id, text=update.message, parse_mode=None
    )
