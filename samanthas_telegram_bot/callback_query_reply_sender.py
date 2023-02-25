from datetime import timedelta
from math import ceil
from typing import Union

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from samanthas_telegram_bot.constants import (
    DAY_OF_WEEK_FOR_INDEX,
    LANGUAGE_CODES,
    LEVELS,
    PHRASES,
    STUDENT_AGE_GROUPS_FOR_TEACHER,
    STUDENT_COMMUNICATION_LANGUAGE_CODES,
    UTC_TIME_SLOTS,
    CallbackData,
    Role,
)
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES


class CallbackQueryReplySender:
    """A helper class that send a reply to user by executing
    `telegram.CallbackQuery.edit_message_text()`.

    Methods in this class are called several times in the bot's code and/or are complex.
    Simple calls to .edit_message_text() can be coded in the bot's code directly.

    Can only be used in callbacks that are handled by `CallbackQueryHandler`.

    Note that all methods in this class are **class methods**. We cannot create an instance of this
    class because context can be different, and especially CallbackQuery object **will** be
    different at each call of the methods.
    """

    @classmethod
    async def ask_class_communication_languages(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks user to choose languages to communicate in (Russian, Ukrainian or any for
        a student; Russian, Ukrainian, any of those two or L2 only for a teacher).
        """

        locale = context.user_data.locale

        if context.user_data.role == Role.TEACHER:
            language_codes = STUDENT_COMMUNICATION_LANGUAGE_CODES[:]
        else:
            # the student cannot choose "L2 only" because that wouldn't make sense
            language_codes = [c for c in STUDENT_COMMUNICATION_LANGUAGE_CODES if c != "l2_only"]

        language_for_callback_data = {
            code: PHRASES[f"class_communication_language_option_{code}"][locale]
            for code in language_codes
        }

        language_buttons = [
            InlineKeyboardButton(text=value, callback_data=key)
            for key, value in language_for_callback_data.items()
        ]
        role = context.user_data.role

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES[f"ask_class_communication_language_{role}"][locale],
                buttons=language_buttons,
                buttons_per_row=1,
                parse_mode=None,
            )
        )

    @classmethod
    async def ask_teacher_peer_help(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a teacher whether they are able to help their fellow teachers."""
        # this question is only asked if teacher is experienced, but the check is done in main.py
        locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=PHRASES[f"option_teacher_peer_help_{option}"][locale],
                callback_data=option,
            )
            for option in (
                "consult",
                "children_group",
                "materials",
                "check_syllabus",
                "feedback",
                "invite",
                "tandem",
            )
            if option not in context.chat_data["peer_help_callback_data"]
        ]

        # the done button must be there right from the start because the teacher may not be willing
        # to provide any kind of peer help

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES["ask_teacher_peer_help"][locale],
                buttons=buttons,
                buttons_per_row=1,
                bottom_row_button=InlineKeyboardButton(
                    PHRASES["ask_teacher_peer_help_done"][locale],
                    callback_data=CallbackData.DONE,
                ),
                parse_mode=None,
            )
        )

    @classmethod
    async def ask_teacher_about_help_with_cv_and_speaking_clubs(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a teacher whether they are able to help students with CV or host speaking clubs."""
        locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=PHRASES[f"option_teacher_help_{option}"][locale],
                callback_data=option,
            )
            for option in ("cv", "speaking_club", "cv_and_speaking_club")
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES["ask_teacher_help_with_cv_and_speaking_clubs"][locale],
                buttons=buttons,
                buttons_per_row=1,
                parse_mode=None,
            )
        )

    @classmethod
    async def ask_teaching_frequency(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a teacher to choose the frequency of their classes."""

        buttons = [
            InlineKeyboardButton(
                text=PHRASES[f"option_frequency_{number}"][context.user_data.locale],
                callback_data=number,
            )
            for number in (1, 2, 3)
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES["ask_teacher_frequency"][context.user_data.locale],
                buttons=buttons,
                buttons_per_row=1,
                parse_mode=None,
            )
        )

    @classmethod
    async def ask_teaching_languages(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
        show_done_button: bool = True,
    ) -> None:
        """Asks a user for them to choose languages to learn/teach."""

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
                callback_data=CallbackData.DONE,
            )

        language_buttons = [
            InlineKeyboardButton(text=value, callback_data=key)
            for key, value in language_for_callback_data.items()
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES[f"ask_teaching_language_{context.user_data.role}"][
                    context.user_data.locale
                ],
                buttons=language_buttons,
                buttons_per_row=3,
                bottom_row_button=done_button,
            )
        )

    @classmethod
    async def ask_language_levels(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
        show_done_button: bool = True,
    ) -> None:
        """Asks a user to choose language level(s)."""

        # if the user has already chosen one level, add "Next" button
        # TODO this button makes the levels go up, user might mistap
        done_button = None

        if show_done_button:
            done_button = InlineKeyboardButton(
                text=PHRASES["ask_teaching_language_level_done"][context.user_data.locale],
                callback_data=CallbackData.DONE,
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

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=text,
                buttons=level_buttons,
                buttons_per_row=3,
                bottom_row_button=done_button,
                parse_mode=None,
            )
        )

    @classmethod
    async def ask_student_age_groups_for_teacher(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a teacher to choose age groups of students."""
        locale = context.user_data.locale

        all_buttons = [
            InlineKeyboardButton(text=PHRASES[f"option_{key}"][locale], callback_data=value)
            for key, value in STUDENT_AGE_GROUPS_FOR_TEACHER.items()
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
                callback_data=CallbackData.DONE,
            )
        )

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES["ask_teacher_student_age_groups"][locale],
                buttons=buttons_to_show,
                buttons_per_row=1,
                bottom_row_button=done_button,
            )
        )

    @classmethod
    async def ask_time_slot(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a user to choose a time slot on one particular day."""

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

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=message_text,
                buttons=buttons,
                buttons_per_row=3,
                bottom_row_button=InlineKeyboardButton(
                    text=PHRASES["ask_slots_next"][context.user_data.locale],
                    callback_data=CallbackData.NEXT,
                ),
            )
        )

    @classmethod
    async def ask_timezone(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks timezone."""

        utc_time = query.message.date

        await query.edit_message_text(
            PHRASES["ask_timezone"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=dlt)).strftime('%H:%M')} ({dlt})",
                            callback_data=dlt,
                        )
                        for dlt in (-8, -7, -6)
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=dlt)).strftime('%H:%M')} ({dlt})",
                            callback_data=dlt,
                        )
                        for dlt in (-5, -4, -3)
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=-1)).strftime('%H:%M')} (-1)",
                            callback_data=-1,
                        ),
                        InlineKeyboardButton(
                            text=f"{utc_time.strftime('%H:%M')} (0)",
                            callback_data=0,
                        ),
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=1)).strftime('%H:%M')} (+1)",
                            callback_data=1,
                        ),
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=2)).strftime('%H:%M')} (+2)",
                            callback_data=2,
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=3)).strftime('%H:%M')} (+3)",
                            callback_data=3,
                        ),
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=4)).strftime('%H:%M')} (+4)",
                            callback_data=4,
                        ),
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=5, minutes=30)).strftime('%H:%M')}"
                            f" (+5:30)",
                            callback_data=5.5,
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=dlt)).strftime('%H:%M')} "
                            f"(+{dlt})",
                            callback_data=dlt,
                        )
                        for dlt in (8, 9, 10)
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=dlt)).strftime('%H:%M')} "
                            f"(+{dlt})",
                            callback_data=dlt,
                        )
                        for dlt in (11, 12, 13)
                    ],
                ]
            ),
        )

    @classmethod
    async def ask_yes_no(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
        question_phrase_internal_id: str,
    ) -> None:
        """Asks "yes" or "no" (localized)."""

        phrase_for_callback_data = {
            option: PHRASES[f"option_{option}"][context.user_data.locale]
            for option in (CallbackData.YES, CallbackData.NO)
        }

        buttons = [
            InlineKeyboardButton(text=value, callback_data=key)
            for key, value in phrase_for_callback_data.items()
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES[question_phrase_internal_id][context.user_data.locale],
                buttons=buttons,
                buttons_per_row=2,
            )
        )

    @staticmethod
    def _make_dict_for_message_with_inline_keyboard(
        message_text: str,
        buttons: list[InlineKeyboardButton],
        buttons_per_row,
        bottom_row_button: InlineKeyboardButton = None,
        parse_mode: Union[ParseMode, None] = ParseMode.MARKDOWN_V2,
    ) -> dict[str, Union[str, str, InlineKeyboardMarkup]]:
        """Makes a message with an inline keyboard, the number of rows in which depends on how many
        buttons are passed. The buttons are evenly distributed over the rows. The last row can
        contain the lone button (that could be e.g. "Next" or "Done").

        Returns dictionary that can be unpacked into await query.edit_message_text()
        """

        number_of_rows = ceil(len(buttons) / buttons_per_row)

        if number_of_rows == 0:
            number_of_rows = 1

        rows = []
        copied_buttons = buttons[:]
        for _ in range(number_of_rows):
            rows += [
                copied_buttons[:buttons_per_row]
            ]  # it works even if there are fewer buttons left
            del copied_buttons[:buttons_per_row]

        if bottom_row_button:
            rows.append([bottom_row_button])

        return {
            "text": message_text,
            "parse_mode": parse_mode,
            "reply_markup": InlineKeyboardMarkup(rows),
        }
