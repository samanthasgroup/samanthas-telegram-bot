from math import ceil
from typing import Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from samanthas_telegram_bot.constants import (
    DAY_OF_WEEK_FOR_INDEX,
    LANGUAGE_CODES,
    LEVELS,
    PHRASES,
    UTC_TIME_SLOTS,
)
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES


def _make_dict_for_message_with_inline_keyboard(
    message_text: str,
    buttons: list[InlineKeyboardButton],
    buttons_per_row,
    bottom_row_button: InlineKeyboardButton = None,
    parse_mode: Union[ParseMode, None] = ParseMode.MARKDOWN_V2,
) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
    """Makes a message with an inline keyboard, the number of rows in which depends on how many
    buttons are passed. The buttons are evenly distributed over the rows. The last row can contain
    the lone button (that could be e.g. "Next" or "Done").

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
        "parse_mode": parse_mode,
        "reply_markup": InlineKeyboardMarkup(rows),
    }


def make_dict_for_message_with_inline_keyboard_with_languages(
    context: CUSTOM_CONTEXT_TYPES,
    show_done_button: bool = True,
) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
    """A helper function that produces data to send to a user for them to choose languages
    to learn/teach.

    Returns a dictionary with message text, parse mode and inline keyboard,
    that can be simply unpacked when passing to `query.edit_message_text()`.
    """

    language_for_callback_data = {
        code: PHRASES[code][context.user_data.locale]
        for code in LANGUAGE_CODES
        if code not in context.user_data.levels_for_teaching_language
    }

    # if the user has already chosen one language, add "Done" button
    done_button = None
    if show_done_button:
        done_button = InlineKeyboardButton(
            text=PHRASES["ask_teaching_language_done"][context.user_data.locale],
            callback_data="done",
        )

    language_buttons = [
        InlineKeyboardButton(text=value, callback_data=key)
        for key, value in language_for_callback_data.items()
    ]

    return _make_dict_for_message_with_inline_keyboard(
        message_text=PHRASES[f"ask_teaching_language_{context.user_data.role}"][
            context.user_data.locale
        ],
        buttons=language_buttons,
        buttons_per_row=4,
        bottom_row_button=done_button,
    )


def make_dict_for_message_with_inline_keyboard_with_language_levels(
    context: CUSTOM_CONTEXT_TYPES,
    show_done_button: bool = True,
) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
    """A helper function that produces data to send to a user for them to choose language level(s).

    Returns a dictionary with message text, parse mode and inline keyboard,
    that can be simply unpacked when passing to `query.edit_message_text()`.
    """

    # if the user has already chosen one level, add "Next" button
    done_button = None

    if show_done_button:
        done_button = InlineKeyboardButton(
            text=PHRASES["ask_teaching_language_level_done"][context.user_data.locale],
            callback_data="done",
        )

    last_language_added = tuple(context.user_data.levels_for_teaching_language.keys())[-1]
    language_name = PHRASES[last_language_added][context.user_data.locale]

    text = (
        f"{PHRASES[f'ask_language_level_{context.user_data.role}'][context.user_data.locale]} "
        f"{language_name}?"
    )

    level_buttons = [
        InlineKeyboardButton(text=level, callback_data=level)
        for level in LEVELS
        if level not in context.user_data.levels_for_teaching_language[last_language_added]
    ]

    return _make_dict_for_message_with_inline_keyboard(
        message_text=text,
        buttons=level_buttons,
        buttons_per_row=3,
        bottom_row_button=done_button,
        parse_mode=None,
    )


def make_dict_for_message_with_inline_keyboard_with_time_slots(
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

    return _make_dict_for_message_with_inline_keyboard(
        message_text=message_text,
        buttons=buttons,
        buttons_per_row=3,
        bottom_row_button=InlineKeyboardButton(
            text=PHRASES["ask_slots_next"][context.user_data.locale],
            callback_data="next",
        ),
    )
