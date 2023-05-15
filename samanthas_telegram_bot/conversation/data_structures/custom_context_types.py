from typing import TYPE_CHECKING

from telegram.ext import CallbackContext, ExtBot

# include custom classes into ContextTypes to get attribute hinting
# (replacing standard dicts with UserData for "user_data" etc.)

# If we import directly and include the custom types without ForwardRef's, we get circular import.
# If we only leave ForwardRefs and don't import with "if TYPE_CHECKING", we get no type hinting.

if TYPE_CHECKING:
    from samanthas_telegram_bot.conversation.data_structures.bot_data import BotData  # noqa
    from samanthas_telegram_bot.conversation.data_structures.chat_data import ChatData  # noqa
    from samanthas_telegram_bot.conversation.data_structures.user_data import UserData  # noqa

CUSTOM_CONTEXT_TYPES = CallbackContext[ExtBot[None], "UserData", "ChatData", "BotData"]
