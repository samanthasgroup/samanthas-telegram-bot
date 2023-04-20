import csv

from telegram import CallbackQuery

from samanthas_telegram_bot.conversation.callbacks.auxil.callback_query_reply_sender import (
    CallbackQueryReplySender,
)
from samanthas_telegram_bot.conversation.constants_enums import DATA_DIR, LANGUAGE_CODES
from samanthas_telegram_bot.conversation.custom_context_types import CUSTOM_CONTEXT_TYPES


def get_questions(lang_code: str, level: str) -> tuple[dict[str, str], ...]:
    """Gets assessment questions, based on language and level"""
    if lang_code not in LANGUAGE_CODES:
        # There is a difference between no test being available (that shouldn't raise an error)
        # and a wrong language code being passed
        raise ValueError(f"Wrong language code {lang_code}")

    # TODO right now one test for all
    path_to_test = DATA_DIR / "assessment_temp.csv"

    with path_to_test.open(encoding="utf-8", newline="") as fh:
        rows = tuple(csv.DictReader(fh))

    return rows


async def prepare_assessment(context: CUSTOM_CONTEXT_TYPES, query: CallbackQuery) -> None:
    """Performs necessary preparatory operations and sends reply with CallbackQueryReplySender."""
    # prepare questions and set index to 0
    context.chat_data["assessment_questions"] = get_questions("en", "A1")  # TODO for now
    context.chat_data["current_question_idx"] = 0
    await CallbackQueryReplySender.ask_start_assessment(context, query)


if __name__ == "__main__":
    get_questions("en", "A1")
