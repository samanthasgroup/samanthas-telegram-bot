from math import ceil
from typing import Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from samanthas_telegram_bot.constants import (
    DAY_OF_WEEK_FOR_INDEX,
    LANGUAGE_CODES,
    PHRASES,
    UTC_TIME_SLOTS,
)
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES


def _make_dict_for_inline_keyboard(
    message_text: str,
    buttons: list[InlineKeyboardButton],
    locale: str,
    buttons_per_row,
    bottom_row_button: InlineKeyboardButton = None,
) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
    """Makes an inline keyboard, the number of rows in which depends on how many buttons
    are passed. The buttons are evenly distributed over the rows. The last row always contains
    the "Next" button.

    Returns dictionary that can be unpacked into query.edit_message_text()
    """

    number_of_rows = ceil(len(buttons) / buttons_per_row)

    if number_of_rows == 0:
        number_of_rows = 1

    rows = [
        buttons[: len(buttons) // number_of_rows],
        buttons[len(buttons) // number_of_rows :],
    ]

    if bottom_row_button:
        rows.append([bottom_row_button])

    return {
        "text": message_text,
        "parse_mode": ParseMode.MARKDOWN_V2,
        "reply_markup": InlineKeyboardMarkup(rows),
    }


def make_dict_for_inline_keyboard_with_languages(
    context: CUSTOM_CONTEXT_TYPES,
) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
    """A helper function that produces data to send to a user for them to choose languages
    to learn/teach.
    Returns a dictionary with message text, parse mode and inline keyboard,
    that can be simply unpacked when passing to `query.edit_message_text()`.
    """

    language_for_callback_data = {
        code: PHRASES[code][context.user_data.locale] for code in LANGUAGE_CODES
    }

    # if the user has already chosen one language, add "Done" button
    done_button = None
    if context.user_data.levels_for_teaching_language:
        done_button = InlineKeyboardButton(
            text=PHRASES["ask_teaching_language_done"][context.user_data.locale],
            callback_data="done",
        )

    language_buttons = [
        InlineKeyboardButton(text=value, callback_data=key)
        for key, value in language_for_callback_data.items()
        if key not in context.user_data.levels_for_teaching_language
    ]

    return _make_dict_for_inline_keyboard(
        message_text=PHRASES[f"ask_teaching_language_{context.user_data.role}"][
            context.user_data.locale
        ],
        buttons=language_buttons,
        locale=context.user_data.locale,
        buttons_per_row=4,
        bottom_row_button=done_button,
    )


def make_dict_for_inline_keyboard_with_time_slots(
    context: CUSTOM_CONTEXT_TYPES,
) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
    """A helper function that produces data to send to a user for them to choose a time slot.
    Returns a dictionary with message text, parse mode and inline keyboard,
    that can be simply unpacked when passing to `query.edit_message_text()`.
    """

    day = DAY_OF_WEEK_FOR_INDEX[context.chat_data["day_idx"]]

    # % 24 is needed to avoid showing 22:00-25:00 to the user
    buttons = [
        InlineKeyboardButton(
            f"{(pair[0] + context.user_data.utc_offset) % 24}:00-"
            f"{(pair[1] + context.user_data.utc_offset) % 24}:00",
            callback_data=f"{pair[0]}-{pair[1]}",  # callback_data is in UTC
        )
        for pair in UTC_TIME_SLOTS
        # exclude slots that user has already selected
        if f"{pair[0]}-{pair[1]}" not in context.user_data.time_slots_for_day[day]
    ]

    message_text = (
        PHRASES["ask_timeslots"][context.user_data.locale]
        + " *"
        + (PHRASES["ask_slots_" + str(context.chat_data["day_idx"])][context.user_data.locale])
        + r"*\?"
    )

    return _make_dict_for_inline_keyboard(
        message_text=message_text,
        buttons=buttons,
        locale=context.user_data.locale,
        buttons_per_row=3,
        bottom_row_button=InlineKeyboardButton(
            text=PHRASES["ask_slots_next"][context.user_data.locale],
            callback_data="next",
        ),
    )
