from telegram import CallbackQuery, Update

from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES


async def answer_callback_query_and_get_data(update: Update) -> tuple[CallbackQuery, str]:
    """Answers CallbackQuery and extracts data. Returns query and its data (string per definition).

    The query itself is usually needed to edit its message text for the next interaction with user.
    """

    query = update.callback_query
    await query.answer()
    return query, query.data


def store_selected_language_level(context: CUSTOM_CONTEXT_TYPES, level: str) -> None:
    """Adds selected level of selected language to `UserData` in 2 versions (logging, backend)."""
    bot_data = context.bot_data
    user_data = context.user_data

    last_language_added = tuple(user_data.levels_for_teaching_language.keys())[-1]

    user_data.levels_for_teaching_language[last_language_added].append(level)
    user_data.language_and_level_ids.append(
        bot_data.language_and_level_id_for_language_id_and_level[(last_language_added, level)]
    )
