from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.custom_updates import (
    ChatwootMessageDirection,
    ChatwootUpdate,
)


async def forward_message_from_chatwoot_to_user(
    update: ChatwootUpdate, context: CUSTOM_CONTEXT_TYPES
) -> None:
    """Callback that forwards messages sent by coordinator in Chatwoot to the user."""
    if update.direction == ChatwootMessageDirection.FROM_CHATWOOT_TO_BOT:
        await context.bot.send_message(
            chat_id=update.bot_chat_id, text=update.message, parse_mode=None
        )
