from telegram.ext import Application, CallbackContext, ExtBot

from samanthas_telegram_bot.data_structures.context_types import BotData, ChatData, UserData


class CustomContext(CallbackContext[ExtBot, UserData, ChatData, BotData]):  # type:ignore[misc]
    """
    Custom CallbackContext class that makes `chat_data` and `user_data` available for updates
    of type `ChatwootUpdate`.
    """

    @classmethod
    def from_update(
        cls,
        update: object,
        application: Application,
    ) -> CallbackContext:
        # if isinstance(update, ChatwootUpdate):
        #     return cls(application=application, chat_id=update.chat_id)  # TODO no user_id now
        return super().from_update(update, application)
