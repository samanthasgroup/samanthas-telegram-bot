from typing import Any

from telegram.ext import CallbackContext, ExtBot

from samanthas_telegram_bot.conversation.data_structures.chat_data import ChatData
from samanthas_telegram_bot.conversation.data_structures.user_data import UserData

# include the custom class into ContextTypes to get attribute hinting
# (replacing standard dict with UserData for "user_data" and ChatData for "chat_data")
CUSTOM_CONTEXT_TYPES = CallbackContext[ExtBot[None], UserData, ChatData, dict[Any, Any]]
