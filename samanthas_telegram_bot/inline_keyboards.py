from math import ceil
from typing import Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from samanthas_telegram_bot.constants import (
    DAY_OF_WEEK_FOR_INDEX,
    LANGUAGE_CODES,
    LEVELS,
    PHRASES,
    STUDENT_COMMUNICATION_LANGUAGE_CODES,
    UTC_TIME_SLOTS,
    Role,
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

    rows = []
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
    }


def make_dict_for_message_with_inline_keyboard_with_student_communication_languages(
    context: CUSTOM_CONTEXT_TYPES,
) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
    """A helper function that produces data to send to a user for them to choose languages
    to communicate in (Russian, Ukrainian or any for a student; Russian, Ukrainian, any of those
    two or L2 only for a teacher).

    Returns a dictionary with message text, parse mode and inline keyboard,
    that can be simply unpacked when passing to `query.edit_message_text()`.
    """

    locale = context.user_data.locale

    if context.user_data.role == Role.TEACHER:
        language_codes = STUDENT_COMMUNICATION_LANGUAGE_CODES[:]
    else:
        # the student cannot choose "L2 only" because that wouldn't make sense
        language_codes = [c for c in STUDENT_COMMUNICATION_LANGUAGE_CODES if c != "l2_only"]

    language_for_callback_data = {
        code: PHRASES[f"student_communication_language_option_{code}"][locale]
        for code in language_codes
    }

    language_buttons = [
        InlineKeyboardButton(text=value, callback_data=key)
        for key, value in language_for_callback_data.items()
    ]
    role = context.user_data.role
    return _make_dict_for_message_with_inline_keyboard(
        message_text=PHRASES[f"ask_student_communication_language_{role}"][locale],
        buttons=language_buttons,
        buttons_per_row=1,
        parse_mode=None,
    )


def make_dict_for_message_with_inline_keyboard_with_teaching_frequency(
    context: CUSTOM_CONTEXT_TYPES,
) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
    """A helper function that produces data to send to a teacher for them to choose the frequency
    of their classes.

    Returns a dictionary with message text, parse mode and inline keyboard,
    that can be simply unpacked when passing to `query.edit_message_text()`.
    """

    buttons = [
        InlineKeyboardButton(
            text=PHRASES[f"option_frequency_{number}"][context.user_data.locale],
            callback_data=number,
        )
        for number in (1, 2, 3)
    ]

    return _make_dict_for_message_with_inline_keyboard(
        message_text=PHRASES["ask_teacher_frequency"][context.user_data.locale],
        buttons=buttons,
        buttons_per_row=1,
        parse_mode=None,
    )


def make_dict_for_message_with_inline_keyboard_with_teaching_languages(
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
        buttons_per_row=3,
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


def make_dict_for_message_with_inline_keyboard_with_student_age_groups_for_teacher(
    context: CUSTOM_CONTEXT_TYPES,
) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
    """A helper function that produces data to send to a teacher for them to use age groups of
    students.

    Returns a dictionary with message text, parse mode and inline keyboard,
    that can be simply unpacked when passing to `query.edit_message_text()`.
    """
    locale = context.user_data.locale

    all_buttons = [
        InlineKeyboardButton(text=PHRASES["option_children"][locale], callback_data="6-11"),
        InlineKeyboardButton(text=PHRASES["option_adolescents"][locale], callback_data="12-17"),
        InlineKeyboardButton(text=PHRASES["option_adults"][locale], callback_data="18-"),
    ]

    buttons_to_show = [
        b
        for b in all_buttons
        if b.callback_data not in context.user_data.teacher_age_groups_of_students
    ]

    # only show "Done" button if the user has selected something on the previous step
    done_button = (
        None
        if buttons_to_show == all_buttons
        else InlineKeyboardButton(
            text=PHRASES["ask_teacher_student_age_groups_done"][locale],
            callback_data="done",
        )
    )

    return _make_dict_for_message_with_inline_keyboard(
        message_text=PHRASES["ask_teacher_student_age_groups"][locale],
        buttons=buttons_to_show,
        buttons_per_row=1,
        bottom_row_button=done_button,
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


def make_dict_for_message_with_yes_no_inline_keyboard(
    context: CUSTOM_CONTEXT_TYPES,
    question_phrase_internal_id: str,
) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
    """A helper function that produces data for an inline keyboard with options "yes" and "no"
    (localized).

    Returns a dictionary with message text, parse mode and inline keyboard,
    that can be simply unpacked when passing to `query.edit_message_text()`.
    """

    phrase_for_callback_data = {
        option: PHRASES[f"option_{option}"][context.user_data.locale] for option in ("yes", "no")
    }

    buttons = [
        InlineKeyboardButton(text=value, callback_data=key)
        for key, value in phrase_for_callback_data.items()
    ]

    return _make_dict_for_message_with_inline_keyboard(
        message_text=PHRASES[question_phrase_internal_id][context.user_data.locale],
        buttons=buttons,
        buttons_per_row=2,
    )
