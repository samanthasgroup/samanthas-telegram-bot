from math import ceil

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.auxil.constants import SPEAKING_CLUB_COORDINATOR_USERNAME
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.conversation.auxil.enums import CommonCallbackData
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import AgeRangeType, LoggingLevel


async def answer_callback_query_and_get_data(update: Update) -> tuple[CallbackQuery, str]:
    """Answers CallbackQuery and extracts data. Returns query and its data (string per definition).

    The query itself is usually needed to edit its message text for the next interaction with user.
    """

    query = update.callback_query
    await query.answer()
    return query, query.data


def make_buttons_with_age_ranges_for_students(
    context: CUSTOM_CONTEXT_TYPES,
) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text=f"{age_range.age_from}-{age_range.age_to}",
            callback_data=age_range.id,
        )
        for age_range in context.bot_data.age_ranges_for_type[AgeRangeType.STUDENT]
    ]


def make_buttons_yes_no(context: CUSTOM_CONTEXT_TYPES) -> list[InlineKeyboardButton]:
    """Produces two buttons for inline keyboard: 'yes' and 'no' (localized)."""
    phrase_for_callback_data = {
        option: context.bot_data.phrases[f"option_{option}"][context.user_data.locale]
        for option in (CommonCallbackData.YES, CommonCallbackData.NO)
    }

    return [
        InlineKeyboardButton(text=value, callback_data=key)
        for key, value in phrase_for_callback_data.items()
    ]


def make_dict_for_message_with_inline_keyboard(
    message_text: str,
    buttons: list[InlineKeyboardButton],
    buttons_per_row: int,
    bottom_row_button: InlineKeyboardButton = None,
    top_row_button: InlineKeyboardButton = None,
    parse_mode: ParseMode | None = None,
) -> dict[str, str | InlineKeyboardMarkup]:
    """Makes a message with an inline keyboard, the number of rows in which depends on how many
    buttons are passed. The buttons are evenly distributed over the rows. The last row can
    contain the lone button (that could be e.g. "Next" or "Done").

    Returns dictionary that can be unpacked into await query.edit_message_text()
    """

    number_of_rows = ceil(len(buttons) / buttons_per_row)

    if number_of_rows == 0:
        number_of_rows = 1

    rows = []

    if top_row_button:
        rows.append([top_row_button])

    copied_buttons = buttons[:]
    for _ in range(number_of_rows):
        rows += [copied_buttons[:buttons_per_row]]  # it works even if there are fewer buttons left
        del copied_buttons[:buttons_per_row]

    if bottom_row_button:
        rows.append([bottom_row_button])

    return {
        "text": message_text,
        "parse_mode": parse_mode,
        "reply_markup": InlineKeyboardMarkup(rows),
        "disable_web_page_preview": True,
    }


def make_dict_for_message_to_ask_age_student(
    context: CUSTOM_CONTEXT_TYPES,
) -> dict[str, str | InlineKeyboardMarkup]:
    return make_dict_for_message_with_inline_keyboard(
        message_text=context.bot_data.phrases["ask_age"][context.user_data.locale],
        buttons=make_buttons_with_age_ranges_for_students(context),
        buttons_per_row=3,
    )


async def notify_speaking_club_coordinator_about_high_level_student(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> None:
    """Lets Speaking Club coordinator know that student is advanced and can only attend SC."""
    user_data = context.user_data

    await logs(
        bot=context.bot,
        text=(
            f"Dear @{SPEAKING_CLUB_COORDINATOR_USERNAME}, student {user_data.first_name} "
            f"{user_data.last_name} ({user_data.email}) has a high level and can only study in "
            "Speaking Club."
        ),
        needs_to_notify_admin_group=True,
        update=update,
    )


async def prepare_assessment(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
    """Resets assessment-related data for student and chooses appropriate assessment questions.

    Run this function only after the student's age has been asked.

    Run this function even in the case the student chooses a language that has
    no assessment to avoid the risk of wrong assessment data being sent in case
    of registration of another student from same Telegram account.
    """
    # prepare questions and set index to 0
    user_data = context.user_data

    age_range_id = user_data.student_age_range_id
    age_range_for_log = f"{user_data.student_age_from}-{user_data.student_age_to} years old"

    try:
        context.chat_data.assessment = context.bot_data.assessment_for_age_range_id[age_range_id]
    except KeyError:
        await logs(
            bot=context.bot,
            text=(
                f"No assessment found for {age_range_for_log}. "
                f"This may be OK if the user really is too young for it."
            ),
            level=LoggingLevel.WARNING,
        )
    else:
        await logs(
            update=update,
            bot=context.bot,
            text=f"Using assessment for {age_range_id=} ({age_range_for_log})",
        )
        user_data.student_assessment_answers = []
        user_data.student_assessment_resulting_level = None
        user_data.student_agreed_to_smalltalk = False
        context.chat_data.current_assessment_question_index = 0
        context.chat_data.current_assessment_question_id = context.chat_data.assessment.questions[
            0
        ].id
        context.chat_data.ids_of_dont_know_options_in_assessment = {
            option.id
            for question in context.chat_data.assessment.questions
            for option in question.options
            if option.means_user_does_not_know_the_answer()
        }
        context.chat_data.assessment_dont_knows_in_a_row = 0


def store_selected_language_level(context: CUSTOM_CONTEXT_TYPES, level: str) -> None:
    """Adds selected level of selected language to `UserData` in 2 versions (logging, backend)."""
    bot_data = context.bot_data
    user_data = context.user_data

    last_language_added = tuple(user_data.levels_for_teaching_language.keys())[-1]

    user_data.levels_for_teaching_language[last_language_added].append(level)
    user_data.language_and_level_ids.append(
        bot_data.language_and_level_id_for_language_id_and_level[(last_language_added, level)]
    )
