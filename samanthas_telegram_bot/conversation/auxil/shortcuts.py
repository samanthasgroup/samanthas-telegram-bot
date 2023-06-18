from telegram import CallbackQuery, Update

from samanthas_telegram_bot.data_structures.context_types import UserData


async def answer_callback_query_and_get_data(update: Update) -> tuple[CallbackQuery, str]:
    """Answers CallbackQuery and extracts data. Returns query and its data (string per definition).

    The query itself is usually needed to edit its message text for the next interaction with user.
    """

    query = update.callback_query
    await query.answer()
    return query, query.data


def get_last_language_added(user_data: UserData) -> str:
    """Returns code (locale) of last teaching language that was added to user's list."""
    if user_data.levels_for_teaching_language is None:
        raise TypeError("User data isn't supposed to be None when calling this function!")
    return tuple(user_data.levels_for_teaching_language.keys())[-1]
