from datetime import timedelta
from math import ceil
from typing import Union

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from samanthas_telegram_bot.conversation.constants_enums import (
    DAY_OF_WEEK_FOR_INDEX,
    LANGUAGE_CODES,
    LEVELS,
    NON_TEACHING_HELP_TYPES,
    PHRASES,
    STUDENT_AGE_GROUPS_FOR_TEACHER,
    STUDENT_COMMUNICATION_LANGUAGE_CODES,
    UTC_TIME_SLOTS,
    CommonCallbackData,
    Role,
    UserDataReviewCategory,
)
from samanthas_telegram_bot.conversation.custom_context_types import CUSTOM_CONTEXT_TYPES

# TODO mark parse mode in phrases.csv so that I don't have to escape full stops etc. everywhere


class CallbackQueryReplySender:
    """A helper class that sends replies to user by executing
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
            )
        )

    @classmethod
    async def ask_how_long_been_learning_english(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a student how long they have been learning English."""
        locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=PHRASES[f"option_{name}"][locale],
                callback_data=name,
            )
            for name in ("less_than_year", "year_or_more")
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES["ask_student_how_long_been_learning_english"][locale],
                buttons=buttons,
                buttons_per_row=2,
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
        done_button = None

        if show_done_button:
            done_button = InlineKeyboardButton(
                text=PHRASES["ask_teaching_language_level_done"][context.user_data.locale],
                callback_data=CommonCallbackData.DONE,
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
                top_row_button=done_button,
            )
        )

    @classmethod
    async def ask_next_assessment_question(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks user the next assessment question."""
        questions = context.chat_data["assessment_questions"]

        buttons = [
            InlineKeyboardButton(
                text=questions[context.chat_data["current_question_idx"]][f"option_{option_idx}"],
                callback_data=option_idx,
            )
            for option_idx in ("1", "2", "3", "4")  # TODO different tests have different amount
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=(
                    f"(Question #{context.chat_data['current_question_idx'] + 1} out of "
                    f"{len(context.chat_data['assessment_questions'])}) "
                    f"{questions[context.chat_data['current_question_idx']]['question']}"
                ),
                buttons=buttons,
                buttons_per_row=2,  # TODO 4 or variable number
                bottom_row_button=InlineKeyboardButton(
                    text=PHRASES["assessment_option_dont_know"][context.user_data.locale],
                    callback_data=CommonCallbackData.DONT_KNOW,
                ),
            )
        )

    @classmethod
    async def ask_non_teaching_help(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks about non-teaching help.

        If this is a student, asks them what help they need.
        If this is a teacher, asks them what help they can provide.
        """
        locale = context.user_data.locale

        # These options match IDs in data migration in django_webapps.  We can leave it like this
        # for now, because bot phrases have to be stored in bot anyway, which means the names
        # also need to be controlled manually even if the types of non-teaching help are received
        # from the back-end.  To completely eliminate the need for manual editing in two places,
        # the bot should receive the bot phrases from there too.
        buttons = [
            InlineKeyboardButton(
                text=PHRASES[f"option_non_teaching_help_{option}"][locale],
                callback_data=option,
            )
            for option in NON_TEACHING_HELP_TYPES
            if option not in context.user_data.non_teaching_help_types
        ]

        # "Done" button must be there right from the start because the teacher may not be willing
        # to provide any kind help or a student may not need any help
        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES[f"ask_non_teaching_help_{context.user_data.role}"][locale],
                buttons=buttons,
                buttons_per_row=1,
                bottom_row_button=InlineKeyboardButton(
                    text=PHRASES["option_non_teaching_help_done"][locale],
                    callback_data=CommonCallbackData.DONE,
                ),
            )
        )

    @classmethod
    async def ask_review_category(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks what info the user wants to change during the review."""

        locale = context.user_data.locale

        options = [
            # Without f-strings they will produce something like <Enum: "name">.
            # An alternative is to use .value attribute.
            f"{UserDataReviewCategory.FIRST_NAME}",
            f"{UserDataReviewCategory.LAST_NAME}",
            f"{UserDataReviewCategory.EMAIL}",
            f"{UserDataReviewCategory.TIMEZONE}",
            f"{UserDataReviewCategory.AVAILABILITY}",
            f"{UserDataReviewCategory.CLASS_COMMUNICATION_LANGUAGE}",
        ]

        if context.user_data.phone_number:
            options.append(f"{UserDataReviewCategory.PHONE_NUMBER}")

        if context.user_data.role == Role.STUDENT:
            options.append(f"{UserDataReviewCategory.STUDENT_AGE_GROUP}")

        # Because of complex logic around English, we will not offer the student to review their
        # language/level for now.  This option will be reserved for teachers.
        if context.user_data.role == Role.TEACHER:
            options.append(f"{UserDataReviewCategory.LANGUAGE_AND_LEVEL}")

        buttons = [
            InlineKeyboardButton(
                text=PHRASES[f"review_option_{option}"][locale], callback_data=option
            )
            for option in options
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES["review_ask_category"][locale],
                buttons=buttons,
                buttons_per_row=1,
            )
        )

    @classmethod
    async def ask_start_assessment(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        locale = context.user_data.locale

        await query.edit_message_text(
            PHRASES["ask_student_start_assessment"][locale],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=PHRASES["assessment_option_start"][locale],
                            callback_data=CommonCallbackData.OK,
                        )
                    ]
                ]
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    @classmethod
    async def ask_student_age(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a student to choose their age group."""
        locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=f"{d['age_from']}-{d['age_to']}",
                callback_data=f"{d['age_from']}-{d['age_to']}",  # can't just leave this arg out
            )
            for d in context.chat_data["age_ranges"]["student"]
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=(
                    f"{PHRASES['student_ukraine_disclaimer'][locale]}\n\n"
                    f"{PHRASES['ask_age'][locale]}"
                ),
                buttons=buttons,
                buttons_per_row=3,
            )
        )

    @classmethod
    async def ask_teacher_age_groups_of_students(
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
                callback_data=CommonCallbackData.DONE,
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
    async def ask_teacher_can_teach_regular_groups_speaking_clubs(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks adult teacher whether can teach regular groups and/or host speaking clubs."""
        # It is possible that an adult teacher only joins the project to host speaking clubs
        locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=PHRASES[f"option_teach_{option}"][locale],
                callback_data=option,
            )
            for option in (
                "group",
                "speaking_club",
                "both",
            )
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES["ask_teacher_group_speaking_club"][locale],
                buttons=buttons,
                buttons_per_row=1,
            )
        )

    @classmethod
    async def ask_teacher_is_over_16_and_ready_to_host_speaking_clubs(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks young teacher whether they are over 16 and ready to host speaking clubs."""
        # This is intended for teachers that are under 18 years old and hence can't teach in
        # regular groups.  The check is done in main.py.
        locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=PHRASES["option_young_teacher_under_16"][locale],
                callback_data=CommonCallbackData.NO,
            ),
            InlineKeyboardButton(
                text=PHRASES["option_young_teacher_over_16_but_no_speaking_club"][locale],
                callback_data=CommonCallbackData.NO,
            ),
            InlineKeyboardButton(
                text=PHRASES["option_young_teacher_over_16_and_ready_for_speaking_club"][locale],
                callback_data=CommonCallbackData.YES,
            ),
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES["ask_if_over_16_and_can_host_speaking_clubs"][locale],
                buttons=buttons,
                buttons_per_row=1,
            )
        )

    @classmethod
    async def ask_teacher_number_of_groups(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a teacher how many groups they want to take."""
        locale = context.user_data.locale
        buttons = [
            InlineKeyboardButton(
                PHRASES[f"option_number_of_groups_{number}"][locale],
                callback_data=number,
            )
            for number in (1, 2)
        ]

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES["ask_teacher_number_of_groups"][locale],
                buttons=buttons,
                buttons_per_row=1,
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

        # "Done" button must be there right from the start because the teacher may not be willing
        # to provide any kind of peer help
        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=PHRASES["ask_teacher_peer_help"][locale],
                buttons=buttons,
                buttons_per_row=1,
                bottom_row_button=InlineKeyboardButton(
                    PHRASES["ask_teacher_peer_help_done"][locale],
                    callback_data=CommonCallbackData.DONE,
                ),
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
                callback_data=CommonCallbackData.DONE,
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
                buttons_per_row=2,
                bottom_row_button=done_button,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        )

    @classmethod
    async def ask_time_slot(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a user to choose a time slot on one particular day."""

        data = context.user_data
        day = DAY_OF_WEEK_FOR_INDEX[context.chat_data["day_idx"]]

        hour = data.utc_offset_hour
        minute = str(data.utc_offset_minute).zfill(2)  # to produce "00" from 0

        # % 24 is needed to avoid showing 22:00-25:00 to the user
        buttons = [
            InlineKeyboardButton(
                f"{(pair[0] + hour) % 24}:{minute}-" f"{(pair[1] + hour) % 24}:{minute}",
                callback_data=f"{pair[0]}-{pair[1]}",  # callback_data is in UTC
            )
            for pair in UTC_TIME_SLOTS
            # exclude slots that user has already selected
            if f"{pair[0]}-{pair[1]}" not in data.time_slots_for_day[day]
        ]

        message_text = (
            PHRASES["ask_timeslots"][data.locale]
            + " *"
            + (PHRASES["ask_slots_" + str(context.chat_data["day_idx"])][data.locale])
            + r"*\?"
        )

        await query.edit_message_text(
            **cls._make_dict_for_message_with_inline_keyboard(
                message_text=message_text,
                buttons=buttons,
                buttons_per_row=3,
                bottom_row_button=InlineKeyboardButton(
                    text=PHRASES["ask_slots_next"][data.locale],
                    callback_data=CommonCallbackData.NEXT,
                ),
                parse_mode=ParseMode.MARKDOWN_V2,
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
                            callback_data=f"{dlt}:00",
                        )
                        for dlt in (-8, -7, -6)
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=dlt)).strftime('%H:%M')} ({dlt})",
                            callback_data=f"{dlt}:00",
                        )
                        for dlt in (-5, -4, -3)
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=-1)).strftime('%H:%M')} (-1)",
                            callback_data="-1:00",
                        ),
                        InlineKeyboardButton(
                            text=f"{utc_time.strftime('%H:%M')} (0)",
                            callback_data="0:00",
                        ),
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=1)).strftime('%H:%M')} (+1)",
                            callback_data="1:00",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=dlt)).strftime('%H:%M')} "
                            f"(+{dlt})",
                            callback_data=f"{dlt}:00",
                        )
                        for dlt in (2, 3, 4)
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=5, minutes=30)).strftime('%H:%M')}"
                            f" (+5:30)",
                            callback_data="5:30",
                        ),
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=7)).strftime('%H:%M')} (+7)",
                            callback_data="7:00",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=dlt)).strftime('%H:%M')} "
                            f"(+{dlt})",
                            callback_data=f"{dlt}:00",
                        )
                        for dlt in (8, 9, 10)
                    ],
                    [
                        InlineKeyboardButton(
                            text=f"{(utc_time + timedelta(hours=dlt)).strftime('%H:%M')} "
                            f"(+{dlt})",
                            callback_data=f"{dlt}:00",
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
        parse_mode: Union[ParseMode, None] = None,
    ) -> None:
        """Asks "yes" or "no" (localized)."""

        phrase_for_callback_data = {
            option: PHRASES[f"option_{option}"][context.user_data.locale]
            for option in (CommonCallbackData.YES, CommonCallbackData.NO)
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
                parse_mode=parse_mode,
            )
        )

    @staticmethod
    def _make_dict_for_message_with_inline_keyboard(
        message_text: str,
        buttons: list[InlineKeyboardButton],
        buttons_per_row,
        bottom_row_button: InlineKeyboardButton = None,
        top_row_button: InlineKeyboardButton = None,
        parse_mode: Union[ParseMode, None] = None,
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

        if top_row_button:
            rows.append([top_row_button])

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