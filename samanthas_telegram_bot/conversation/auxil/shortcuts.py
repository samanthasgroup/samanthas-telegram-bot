from telegram import CallbackQuery, Update


async def answer_callback_query_and_get_data(update: Update) -> tuple[CallbackQuery, str]:
    """Answers CallbackQuery and extracts data. Returns query and its data (string per definition).

    The query itself is usually needed to edit its message text for the next interaction with user.
    """

    query = update.callback_query
    await query.answer()
    return query, query.data
