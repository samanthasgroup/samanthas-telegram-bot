from telegram.ext import CallbackContext, ExtBot

from samanthas_telegram_bot.conversation.data_structures.bot_data import BotData
from samanthas_telegram_bot.conversation.data_structures.chat_data import ChatData
from samanthas_telegram_bot.conversation.data_structures.user_data import UserData

# include custom classes into ContextTypes to get attribute hinting
# (replacing standard dicts with UserData for "user_data" etc.)
CUSTOM_CONTEXT_TYPES = CallbackContext[ExtBot[None], UserData, ChatData, BotData]
