from typing import Any

from telegram.ext import CallbackContext, ExtBot

from samanthas_telegram_bot.conversation.user_data import UserData

# include the custom class into ContextTypes to get attribute hinting
# (replacing standard dict with UserData for "user_data")
CUSTOM_CONTEXT_TYPES = CallbackContext[ExtBot[None], UserData, dict[Any, Any], dict[Any, Any]]
