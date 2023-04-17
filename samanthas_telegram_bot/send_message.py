# This module contains some send_message operations that are too complex to be included in the main
# code, and at the same time need to run multiple times.

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode

from samanthas_telegram_bot.constants import PHRASES, ChatMode, Role
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES


async def send_message_for_phone_number(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
    """Sends a message to ask for phone number."""
    await update.effective_chat.send_message(
        PHRASES["ask_phone"][context.user_data.locale],
        disable_web_page_preview=True,  # the message contains link to site with country codes
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardMarkup(
            [
                [
                    KeyboardButton(
                        text=PHRASES["share_phone"][context.user_data.locale], request_contact=True
                    )
                ]
            ]
        ),
    )


async def send_message_for_reviewing_user_data(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> None:
    """Sends a to the user for them to review their basic info."""
    u_data = context.user_data

    if u_data.role == Role.TEACHER and context.chat_data["mode"] == ChatMode.NORMAL:
        u_data.teacher_additional_skills_comment = update.message.text

    locale = u_data.locale

    message = (
        f"{PHRASES['ask_review'][locale]}\n\n"
        f"{PHRASES['review_first_name'][locale]}: {u_data.first_name}\n"
        f"{PHRASES['review_last_name'][locale]}: {u_data.last_name}\n"
        f"{PHRASES['review_email'][locale]}: {u_data.email}\n"
    )

    if u_data.role == Role.STUDENT:
        message += (
            f"{PHRASES['review_student_age_group'][locale]}: {u_data.student_age_from}-"
            f"{u_data.student_age_to}\n"
        )

    if context.user_data.tg_username:
        message += f"{PHRASES['review_username'][locale]} (@{u_data.tg_username})\n"
    if context.user_data.phone_number:
        message += f"{PHRASES['review_phone_number'][locale]}: {u_data.phone_number}\n"

    if context.user_data.utc_offset > 0:
        message += f"{PHRASES['review_timezone'][locale]}: UTC+{u_data.utc_offset}\n"
    elif context.user_data.utc_offset < 0:
        message += f"{PHRASES['review_timezone'][locale]}: UTC{u_data.utc_offset}\n"
    else:
        message += f"\n{PHRASES['review_timezone'][locale]}: UTC\n"

    message += f"\n{PHRASES['review_availability'][locale]}:\n"
    # The dictionary of days contains keys for all days of week. Only display the days to the user
    # that they have chosen slots for:
    for idx, day in enumerate(u_data.time_slots_for_day):
        slots = u_data.time_slots_for_day[day]
        if slots:
            message += f"{PHRASES['ask_slots_' + str(idx)][locale]}: "
        # sort by first part of slot as a number (otherwise "8:00" will be after "11:00")
        for slot in sorted(slots, key=lambda s: int(s.split("-")[0])):
            # user must see their slots in their chosen timezone
            hour_from, hour_to = slot.split("-")
            message += (
                f" {int(hour_from) + u_data.utc_offset}:00-{int(hour_to) + u_data.utc_offset}:00;"
            )
        else:  # remove last semicolon, end day with line break
            message = message[:-1] + "\n"
    message += "\n"

    # Because of complex logic around English, we will not offer the student to review their
    # language/level for now.  This option will be reserved for teachers.
    if context.user_data.role == Role.TEACHER:
        message += f"{PHRASES['review_languages_levels'][locale]}:\n"
        for language in u_data.levels_for_teaching_language:
            message += f"{PHRASES[language][locale]}: "
            message += ", ".join(sorted(u_data.levels_for_teaching_language[language])) + "\n"
        message += "\n"

    message += f"{PHRASES['review_communication_language'][locale]}: "
    message += (
        PHRASES[f"class_communication_language_option_{u_data.communication_language_in_class}"][
            locale
        ]
        + "\n"
    )

    buttons = [
        InlineKeyboardButton(
            text=PHRASES["review_reaction_" + option][context.user_data.locale],
            callback_data=option,
        )
        for option in ("yes", "no")
    ]

    await update.effective_chat.send_message(
        text=message,
        # each button in a separate list to make them show in one column
        reply_markup=InlineKeyboardMarkup([[buttons[0]], [buttons[1]]]),
    )
