from datetime import timedelta

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from bot.auxil.log_and_notify import logs
from bot.conversation.auxil.enums import CommonCallbackData, UserDataReviewCategory
from bot.conversation.auxil.helpers import (
    make_buttons_yes_no,
    make_dict_for_message_to_ask_age_student,
    make_dict_for_message_with_inline_keyboard,
)
from bot.data_structures.constants import (
    NON_TEACHING_HELP_TYPES,
    STUDENT_COMMUNICATION_LANGUAGE_CODES,
    TEACHER_PEER_HELP_TYPES,
)
from bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from bot.data_structures.enums import AgeRangeType, LoggingLevel, Role
from bot.data_structures.literal_types import Locale
from bot.data_structures.models import AssessmentQuestion


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

        locale: Locale = context.user_data.locale

        if context.user_data.role == Role.TEACHER:
            language_codes = STUDENT_COMMUNICATION_LANGUAGE_CODES[:]
        else:
            # student or coordinator cannot choose "L2 only" because that wouldn't make sense
            language_codes = tuple(
                c for c in STUDENT_COMMUNICATION_LANGUAGE_CODES if c != "l2_only"
            )

        language_for_callback_data = {
            code: context.bot_data.phrases[f"class_communication_language_option_{code}"][locale]
            for code in language_codes
        }

        language_buttons = [
            InlineKeyboardButton(text=value, callback_data=key)
            for key, value in language_for_callback_data.items()
        ]
        role = context.user_data.role

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases[f"ask_class_communication_language_{role}"][
                    locale
                ],
                buttons=language_buttons,
                buttons_per_row=1,
            )
        )

    @classmethod
    async def ask_first_name(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Ask first name."""

        locale: Locale = context.user_data.locale
        await query.edit_message_text(
            context.bot_data.phrases["ask_first_name"][locale],
            reply_markup=InlineKeyboardMarkup([]),
        )

    @classmethod
    async def ask_how_long_been_learning_english(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a student how long they have been learning English."""
        locale: Locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=context.bot_data.phrases[f"option_{name}"][locale],
                callback_data=name,
            )
            for name in ("less_than_year", "year_or_more")
        ]

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases[
                    "ask_student_how_long_been_learning_english"
                ][locale],
                buttons=buttons,
                buttons_per_row=2,
            )
        )

    @classmethod
    async def ask_language_level(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
        show_done_button: bool = True,
    ) -> None:
        """Asks a user to choose language level(s)."""

        locale: Locale = context.user_data.locale

        # if the user has already chosen one level, add "Next" button
        done_button = None

        if show_done_button:
            done_button = InlineKeyboardButton(
                text=context.bot_data.phrases["ask_teaching_language_level_done"][locale],
                callback_data=CommonCallbackData.NEXT,
            )

        last_language_added = tuple(context.user_data.levels_for_teaching_language.keys())[-1]
        language_name = context.bot_data.phrases[last_language_added][locale]

        text = (
            f"{context.bot_data.phrases[f'ask_language_level_{context.user_data.role}'][locale]} "
            f"{language_name}?"
        )

        # different languages have different set of levels they can be taught at
        relevant_levels = (
            item.level
            for item in context.bot_data.language_and_level_objects_for_language_id[
                last_language_added
            ]
        )
        level_buttons = [
            InlineKeyboardButton(text=level, callback_data=level)
            for level in relevant_levels
            if level not in context.user_data.levels_for_teaching_language[last_language_added]
        ]

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
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
        questions = context.chat_data.assessment.questions
        index = context.chat_data.current_assessment_question_index
        current_question: AssessmentQuestion = questions[index]

        await logs(
            bot=context.bot,
            level=LoggingLevel.DEBUG,
            text=(
                f"Preparing to ask question #{index + 1}"
                f" of {len(context.chat_data.assessment.questions)}, QID {current_question.id}"
            ),
        )

        buttons = [
            InlineKeyboardButton(text=option.text, callback_data=option.id)
            for option in current_question.options
        ]
        locale: Locale = context.user_data.locale
        abort_button = InlineKeyboardButton(
            text=context.bot_data.phrases["assessment_option_abort"][locale],
            callback_data=CommonCallbackData.ABORT,
        )

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=(
                    f"Question {index + 1} out of "
                    f"{len(context.chat_data.assessment.questions)}\n\n"
                    f"{current_question.text}"
                ),
                buttons=buttons,
                buttons_per_row=2,
                bottom_row_button=(
                    abort_button if context.chat_data.assessment_dont_knows_in_a_row >= 5 else None
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
        locale: Locale = context.user_data.locale

        # These options match IDs in data migration in django_webapps.  We can leave it like this
        # for now, because bot phrases have to be stored in bot anyway, which means the names
        # also need to be controlled manually even if the types of non-teaching help are received
        # from the back-end.  To completely eliminate the need for manual editing in two places,
        # the bot should receive the bot phrases from there too.
        buttons = [
            InlineKeyboardButton(
                text=context.bot_data.phrases[f"option_non_teaching_help_{option}"][locale],
                callback_data=option,
            )
            for option in NON_TEACHING_HELP_TYPES
            if option not in context.user_data.non_teaching_help_types
        ]

        # "Done" button must be there right from the start because the teacher may not be willing
        # to provide any kind help or a student may not need any help
        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases[
                    f"ask_non_teaching_help_{context.user_data.role}"
                ][locale],
                buttons=buttons,
                buttons_per_row=1,
                bottom_row_button=InlineKeyboardButton(
                    text=context.bot_data.phrases["option_non_teaching_help_done"][locale],
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

        user_data = context.user_data
        locale: Locale = user_data.locale

        options = [
            # Without f-strings they will produce something like <Enum: "name">.
            # An alternative is to use .value attribute.
            f"{UserDataReviewCategory.FIRST_NAME}",
            f"{UserDataReviewCategory.LAST_NAME}",
            f"{UserDataReviewCategory.EMAIL}",
            f"{UserDataReviewCategory.CLASS_COMMUNICATION_LANGUAGE}",
            f"{UserDataReviewCategory.TIMEZONE}",
        ]

        if user_data.role != Role.COORDINATOR:
            options += [
                f"{UserDataReviewCategory.DAY_AND_TIME_SLOTS}",
            ]

        if user_data.phone_number:
            options.append(f"{UserDataReviewCategory.PHONE_NUMBER}")

        if user_data.role == Role.STUDENT:
            options.append(f"{UserDataReviewCategory.STUDENT_AGE_GROUPS}")

        # Because of complex logic around English, we will not offer the student to review their
        # language/level for now.  This option will be reserved for teachers.
        if user_data.role == Role.TEACHER:
            options.extend(
                [
                    f"{UserDataReviewCategory.LANGUAGES_AND_LEVELS}",
                    f"{UserDataReviewCategory.STUDENT_AGE_GROUPS}",
                ]
            )

        buttons = [
            InlineKeyboardButton(
                text=context.bot_data.phrases[f"review_option_{option}"][locale],
                callback_data=option,
            )
            for option in options
        ]

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases["review_ask_category"][locale],
                buttons=buttons,
                buttons_per_row=1,
            )
        )

    @classmethod
    async def ask_role(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Ask role (student, teacher or coordinator)."""
        locale: Locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=context.bot_data.phrases[f"option_{role}"][locale],
                callback_data=role,
            )
            for role in (Role.STUDENT, Role.TEACHER, Role.COORDINATOR)
        ]

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases["ask_role"][locale],
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
        locale: Locale = context.user_data.locale

        await query.edit_message_text(
            context.bot_data.phrases["ask_student_start_assessment"][locale],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=context.bot_data.phrases["assessment_option_start"][locale],
                            callback_data=CommonCallbackData.OK,
                        )
                    ]
                ]
            ),
            parse_mode=ParseMode.HTML,
        )

    @classmethod
    async def ask_student_age_group(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks student about their age group."""
        await query.edit_message_text(**make_dict_for_message_to_ask_age_student(context))

    @classmethod
    async def ask_teacher_or_coordinator_additional_help(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks about additional help the coordinator/teacher can provide (in free text)."""

        user_data = context.user_data
        locale: Locale = user_data.locale
        role: Role = user_data.role

        await query.edit_message_text(
            context.bot_data.phrases[f"ask_{role}_any_additional_help"][locale],
            reply_markup=InlineKeyboardMarkup([]),
        )

    @classmethod
    async def ask_teacher_age_groups_of_students(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a teacher to choose age groups of students."""
        locale: Locale = context.user_data.locale

        all_buttons = [
            InlineKeyboardButton(
                text=context.bot_data.phrases[age_range.bot_phrase_id][locale],
                callback_data=age_range.id,
            )
            for age_range in context.bot_data.age_ranges_for_type[AgeRangeType.TEACHER]
        ]

        buttons_to_show = [
            b
            for b in all_buttons
            if b.callback_data not in context.user_data.teacher_student_age_range_ids
        ]

        # only show "Done" button if the user has selected something on the previous step
        done_button = (
            None
            if buttons_to_show == all_buttons
            else InlineKeyboardButton(
                text=context.bot_data.phrases["ask_teacher_student_age_groups_done"][locale],
                callback_data=CommonCallbackData.DONE,
            )
        )

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases["ask_teacher_student_age_groups"][locale],
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
        locale: Locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=context.bot_data.phrases[f"option_teach_{option}"][locale],
                callback_data=option,
            )
            for option in (
                "group",
                "speaking_club",
                "both",
            )
        ]

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases["ask_teacher_group_speaking_club"][locale],
                buttons=buttons,
                buttons_per_row=1,
            )
        )

    @classmethod
    async def ask_young_teacher_is_over_16_and_ready_to_host_speaking_clubs(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks young teacher whether they are over 16 and ready to host speaking clubs."""
        # This is intended for teachers that are under 18 years old and hence can't teach in
        # regular groups.  The check is done in main.py.
        locale: Locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=context.bot_data.phrases["option_young_teacher_under_16"][locale],
                callback_data=CommonCallbackData.NO,
            ),
            InlineKeyboardButton(
                text=context.bot_data.phrases["option_young_teacher_over_16_but_no_speaking_club"][
                    locale
                ],
                callback_data=CommonCallbackData.NO,
            ),
            InlineKeyboardButton(
                text=context.bot_data.phrases[
                    "option_young_teacher_over_16_and_ready_for_speaking_club"
                ][locale],
                callback_data=CommonCallbackData.YES,
            ),
        ]

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases[
                    "ask_if_over_16_and_can_host_speaking_clubs"
                ][locale],
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
        locale: Locale = context.user_data.locale
        buttons = [
            InlineKeyboardButton(
                context.bot_data.phrases[f"option_number_of_groups_{number}"][locale],
                callback_data=number,
            )
            for number in (1, 2)
        ]

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases["ask_teacher_number_of_groups"][locale],
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
        locale: Locale = context.user_data.locale

        buttons = [
            InlineKeyboardButton(
                text=context.bot_data.phrases[f"option_teacher_peer_help_{option}"][locale],
                callback_data=option,
            )
            for option in TEACHER_PEER_HELP_TYPES
            if option not in context.chat_data.peer_help_callback_data
        ]

        # "Done" button must be there right from the start because the teacher may not be willing
        # to provide any kind of peer help
        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases["ask_teacher_peer_help"][locale],
                buttons=buttons,
                buttons_per_row=1,
                bottom_row_button=InlineKeyboardButton(
                    context.bot_data.phrases["ask_teacher_peer_help_done"][locale],
                    callback_data=CommonCallbackData.DONE,
                ),
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

        locale: Locale = context.user_data.locale

        language_for_callback_data = {
            code: context.bot_data.phrases[code][locale]
            for code in context.bot_data.sorted_language_ids
            if code not in context.user_data.levels_for_teaching_language
        }

        # if the user has already chosen one language, add "Done" button
        done_button = None
        if show_done_button:
            done_button = InlineKeyboardButton(
                text=context.bot_data.phrases["ask_teaching_language_done"][locale],
                callback_data=CommonCallbackData.DONE,
            )

        language_buttons = [
            InlineKeyboardButton(text=value, callback_data=key)
            for key, value in language_for_callback_data.items()
        ]

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases[
                    f"ask_teaching_language_{context.user_data.role}"
                ][locale],
                buttons=language_buttons,
                buttons_per_row=2,
                bottom_row_button=done_button,
                parse_mode=ParseMode.HTML,
            )
        )

    @classmethod
    async def ask_time_slot(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks a user to choose a time slot on one particular day."""

        bot_data = context.bot_data
        user_data = context.user_data
        locale: Locale = user_data.locale

        day_index = context.chat_data.day_index

        offset_hour = user_data.utc_offset_hour
        offset_minute = str(user_data.utc_offset_minute).zfill(2)  # to produce "00" from 0

        # % 24 is needed to avoid showing 22:00-25:00 to the user
        buttons = [
            InlineKeyboardButton(
                f"{(slot.from_utc_hour + offset_hour) % 24}:{offset_minute}-"
                f"{(slot.to_utc_hour + offset_hour) % 24}:{offset_minute}",
                callback_data=slot.id,
            )
            for slot in bot_data.day_and_time_slots_for_day_index[day_index]
            # exclude slots that user already selected
            if slot.id not in user_data.day_and_time_slot_ids
        ]

        phrases = bot_data.phrases
        message_text = (
            phrases["ask_timeslots"][locale]
            + " <strong>"
            + (phrases["ask_slots_" + str(day_index)][locale])
            + r"</strong>? ✎"
        )

        # The message explaining how multiselect works is pretty long,
        # so better to only show it once, at the beginning
        if day_index == 0:
            message_text += f"\n\n{phrases['note_multiselect'][locale]}"

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=message_text,
                buttons=buttons,
                buttons_per_row=3,
                bottom_row_button=InlineKeyboardButton(
                    text=phrases["ask_slots_next"][locale],
                    callback_data=CommonCallbackData.NEXT,
                ),
                parse_mode=ParseMode.HTML,
            )
        )

    @classmethod
    async def ask_timezone(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Asks timezone."""

        locale: Locale = context.user_data.locale
        utc_time = query.message.date

        await query.edit_message_text(
            context.bot_data.phrases["ask_timezone"][locale],
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
        parse_mode: ParseMode | None = ParseMode.HTML,
    ) -> None:
        """Asks "yes" or "no" (localized)."""

        locale: Locale = context.user_data.locale

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases[question_phrase_internal_id][locale],
                buttons=make_buttons_yes_no(context),
                buttons_per_row=2,
                parse_mode=parse_mode,
            )
        )

    @classmethod
    async def send_smalltalk_url(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Sends message with SmallTalk URL to the user."""
        bot_data = context.bot_data
        locale: Locale = context.user_data.locale
        url = context.user_data.student_smalltalk_interview_url

        await query.edit_message_text(
            bot_data.phrases["give_smalltalk_url"][locale]
            + (
                f'\n\n<a href="{url}"><strong>'
                f'{bot_data.phrases["give_smalltalk_url_link"][locale]}'
                "</strong></a>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            bot_data.phrases["answer_smalltalk_done"][locale],
                            callback_data=CommonCallbackData.DONE,
                        )
                    ]
                ]
            ),
        )

    @classmethod
    async def show_gdpr_disclaimer(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Show disclaimer on data processing according to GDPR."""
        locale: Locale = context.user_data.locale

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases["gdpr_disclaimer"][locale],
                buttons=cls._create_disclaimer_buttons(context),
                buttons_per_row=2,
                parse_mode=ParseMode.HTML,
            )
        )

    @classmethod
    async def show_general_disclaimer(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Show general disclaimer on volunteering with SSG (message text depends on role)."""
        user_data = context.user_data
        locale: Locale = user_data.locale
        role: Role = user_data.role

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases[f"general_disclaimer_{role}"][locale],
                buttons=cls._create_disclaimer_buttons(context),
                buttons_per_row=2,
                parse_mode=ParseMode.HTML,
            )
        )

    @classmethod
    async def show_legal_disclaimer(
        cls,
        context: CUSTOM_CONTEXT_TYPES,
        query: CallbackQuery,
    ) -> None:
        """Show disclaimer on legal risks of volunteering for an NGO for Russian citizens."""
        locale: Locale = context.user_data.locale

        await query.edit_message_text(
            **make_dict_for_message_with_inline_keyboard(
                message_text=context.bot_data.phrases["legal_disclaimer"][locale],
                buttons=cls._create_disclaimer_buttons(context),
                buttons_per_row=2,
                parse_mode=ParseMode.HTML,
            )
        )

    @staticmethod
    def _create_disclaimer_buttons(context: CUSTOM_CONTEXT_TYPES) -> list[InlineKeyboardButton]:
        locale: Locale = context.user_data.locale

        phrase_for_callback_data = {
            option: context.bot_data.phrases[f"disclaimer_option_{option}"][locale]
            for option in (CommonCallbackData.OK, CommonCallbackData.ABORT)
        }

        return [
            InlineKeyboardButton(text=value, callback_data=key)
            for key, value in phrase_for_callback_data.items()
        ]
