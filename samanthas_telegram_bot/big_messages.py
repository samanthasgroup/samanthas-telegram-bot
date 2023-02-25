from telegram import Update

from samanthas_telegram_bot.constants import PHRASES, Role
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES


def compose_message_for_reviewing_user_data(update: Update, context: CUSTOM_CONTEXT_TYPES) -> str:
    """Composes the message to be shown to the user for them to review their basic info."""
    u_data = context.user_data

    if u_data.role == Role.TEACHER:
        u_data.teacher_additional_skills_comment = update.message.text

    locale = u_data.locale

    message = (
        f"{PHRASES['ask_review'][locale]}\n\n"
        f"{PHRASES['review_first_name'][locale]}: {u_data.first_name}\n"
        f"{PHRASES['review_last_name'][locale]}: {u_data.last_name}\n"
        f"{PHRASES['review_email'][locale]}: {u_data.email}\n"
    )

    if u_data.role == Role.STUDENT:
        message += f"{PHRASES['review_student_age_group'][locale]}: {u_data.student_age_from}-"
        f"{u_data.student_age_from}\n"

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
        for slot in sorted(slots):
            # user must see their slots in their chosen timezone
            hour_from, hour_to = slot.split("-")
            message += (
                f" {int(hour_from) + u_data.utc_offset}:00-{int(hour_to) + u_data.utc_offset}:00;"
            )
        else:  # remove last semicolon, end day with line break
            message = message[:-1] + "\n"
    message += "\n"

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

    return message
