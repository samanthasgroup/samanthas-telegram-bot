import logging
import os
import re
from collections import defaultdict
from datetime import timedelta
from enum import IntEnum, auto

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from samanthas_telegram_bot.callback_query_reply_sender import (
    CallbackQueryReplySender as CQReplySender,
)
from samanthas_telegram_bot.constants import (
    DAY_OF_WEEK_FOR_INDEX,
    EMAIL_PATTERN,
    LOCALES,
    PHONE_PATTERN,
    PHRASES,
    CallbackData,
    Role,
)
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.user_data import UserData

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class State(IntEnum):
    """Provides integer keys for the dictionary of states for ConversationHandler."""

    IS_REGISTERED = auto()
    FIRST_NAME_OR_BYE = auto()
    ROLE = auto()
    AGE = auto()
    LAST_NAME = auto()
    SOURCE = auto()
    CHECK_USERNAME = auto()
    PHONE_NUMBER = auto()
    EMAIL = auto()
    TIMEZONE = auto()
    TIME_SLOTS_START = auto()
    TIME_SLOTS_MENU = auto()
    TEACHING_LANGUAGE = auto()
    LEVEL = auto()
    COMMUNICATION_LANGUAGE_IN_CLASS = auto()
    NUMBER_OF_GROUPS_OR_FREQUENCY = auto()
    TEACHING_FREQUENCY = auto()
    PREFERRED_STUDENT_AGE_GROUPS_START = auto()
    PREFERRED_STUDENT_AGE_GROUPS_MENU = auto()
    ADDITIONAL_SKILLS = auto()
    COMMENT = auto()


async def start(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Starts the conversation and asks the user about the language they want to communicate in."""

    logger.info(f"Chat ID: {update.effective_chat.id}")

    context.user_data.days = []
    context.user_data.time = []

    greeting = ""
    for locale in LOCALES:
        greeting += (
            f"{PHRASES['hello'][locale]} {update.message.from_user.first_name}! "
            f"{PHRASES['choose_language_of_conversation'][locale]}\n\n"
        )

    await update.message.reply_text(
        greeting,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="українською",
                        callback_data="ua",
                    ),
                    InlineKeyboardButton(
                        text="in English",
                        callback_data="en",
                    ),
                    InlineKeyboardButton(
                        text="по-русски",
                        callback_data="ru",
                    ),
                ],
            ]
        ),
    )

    return State.IS_REGISTERED


async def save_interface_lang_ask_if_already_registered(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Stores the interface language and asks the user if they are already registered."""

    query = update.callback_query
    await query.answer()
    context.user_data.locale = query.data

    await CQReplySender.ask_yes_no(
        context,
        query,
        question_phrase_internal_id="ask_already_with_us",
    )

    return State.FIRST_NAME_OR_BYE


async def redirect_to_coordinator_if_registered_ask_first_name(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If user is already registered, redirect to coordinator. Otherwise, ask for first name."""

    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.YES:
        # TODO actual link to chat
        await query.edit_message_text(
            PHRASES["reply_go_to_other_chat"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return ConversationHandler.END

    await query.edit_message_text(
        # the message is the same for it to look like an interactive menu
        PHRASES["ask_first_name"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup([]),
    )
    return State.ROLE


async def save_first_name_ask_role(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the first name and asks the user if they want to become a student or a teacher.
    The question about their age will depend on this answer.
    """
    context.user_data.first_name = update.message.text

    await update.message.reply_text(
        PHRASES["ask_role"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=PHRASES[f"option_{role}"][context.user_data.locale],
                        callback_data=role,
                    )
                    for role in (Role.STUDENT, Role.TEACHER)
                ],
            ]
        ),
    )
    return State.AGE


async def save_role_ask_age(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the role and asks the user what their age is (the question depends on role)."""

    query = update.callback_query
    await query.answer()

    context.user_data.role = query.data

    if context.user_data.role == Role.STUDENT:
        student_ages = [
            ["6-8", "9-11", "12-14", "15-17"],
            ["18-20", "21-25", "26-30", "31-35"],
            ["36-40", "41-45", "46-50", "51-55"],
            ["56-60", "61-65", "66-70", "71-75"],
            ["76-80", "81-65", "86-90", "91-95"],
        ]

        rows_of_buttons = [
            [InlineKeyboardButton(text, callback_data=text) for text in row]
            for row in student_ages
        ]

        await query.edit_message_text(
            PHRASES["ask_age"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup(rows_of_buttons),
        )
    else:
        await CQReplySender.ask_yes_no(
            context,
            query,
            question_phrase_internal_id="ask_if_18",
        )

    return State.LAST_NAME


async def save_age_ask_last_name(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """For students, stores age. For teachers, checks if they are above 18. Asks teachers above 18
    and all students to give their last name.
    """

    query = update.callback_query
    await query.answer()

    # end conversation for would-be teachers that are minors
    if context.user_data.role == Role.TEACHER and query.data == CallbackData.NO:
        # TODO actual link to chat
        await query.edit_message_text(
            PHRASES["reply_under_18"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return ConversationHandler.END

    if context.user_data.role == Role.STUDENT:
        context.user_data.age = query.data

    await query.edit_message_text(PHRASES["ask_last_name"][context.user_data.locale])
    return State.SOURCE


async def save_last_name_ask_source(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the last name and asks the user how they found out about Samantha's Group."""

    # It is impossible to send an empty message, but if for some reason user edits their previous
    # message, an update will be issued, but .message attribute will be none.
    # This will trigger an exception, although the bot won't stop working.  Still we don't want it.
    # So in this case just wait for user to type in the actual new message by returning him to the
    # same state again.
    # This "if" can't be easily factored out because the state returned is different in every
    # callback.
    # TODO an enhancement could be to store the information from the edited message
    if update.message is None:
        return State.SOURCE

    context.user_data.last_name = update.message.text
    await update.effective_chat.send_message(PHRASES["ask_source"][context.user_data.locale])
    return State.CHECK_USERNAME


async def save_source_check_username(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the source of knowledge about SSG, checks Telegram nickname or asks for
    phone number.
    """

    if update.message is None:
        return State.CHECK_USERNAME

    context.user_data.source = update.message.text

    username = update.effective_user.username

    if username:
        await update.effective_chat.send_message(
            f"{PHRASES['ask_username_1'][context.user_data.locale]} @{username}"
            f"{PHRASES['ask_username_2'][context.user_data.locale]}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=PHRASES[f"username_reply_{option}"][context.user_data.locale],
                            callback_data=f"store_username_{option}",
                        )
                        for option in (CallbackData.YES, CallbackData.NO)
                    ],
                ]
            ),
        )

    return State.PHONE_NUMBER


async def save_username_ask_phone(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """If user's username was empty or they chose to provide a phone number, ask for it."""

    username = update.effective_user.username

    query = update.callback_query
    await query.answer()

    if query.data == "store_username_yes" and username:
        context.user_data.username = username
        logger.info(f"Username: {username}. Will be stored in the database.")
        await query.edit_message_text(
            PHRASES["ask_email"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return State.TIMEZONE

    context.user_data.username = None
    await query.delete_message()

    await update.effective_chat.send_message(
        PHRASES["ask_phone"][context.user_data.locale],
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

    return State.EMAIL


async def save_phone_ask_email(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the phone number and asks for email."""

    if update.message is None:
        return State.EMAIL

    # just in case: deleting spaces and hyphens
    text = (
        update.message.text.replace("-", "").replace(" ", "").strip()
        if update.message.text
        else ""
    )

    if not (update.message.contact or PHONE_PATTERN.match(text)):
        await update.message.reply_text(
            PHRASES["invalid_phone_number"][context.user_data.locale],
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.EMAIL

    if update.message.contact:
        context.user_data.phone_number = update.message.contact.phone_number
    else:
        context.user_data.phone_number = text

    await update.message.reply_text(
        PHRASES["ask_email"][context.user_data.locale],
        reply_markup=ReplyKeyboardRemove(),
    )
    logger.info(f"Phone: {context.user_data.phone_number}")
    return State.TIMEZONE


async def save_email_ask_timezone(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the email and asks for timezone."""

    if update.message is None:
        return State.TIMEZONE

    email = update.message.text.strip()
    if not EMAIL_PATTERN.match(email):
        await update.message.reply_text(
            "Please provide a valid email",
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.TIMEZONE
    context.user_data.email = email

    timestamp = update.message.date

    await update.message.reply_text(
        PHRASES["ask_timezone"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=f"{(timestamp + timedelta(hours=delta)).strftime('%H:%M')} ({delta})",
                        callback_data=delta,
                    )
                    for delta in (-8, -7, -6)
                ],
                [
                    InlineKeyboardButton(
                        text=f"{(timestamp + timedelta(hours=delta)).strftime('%H:%M')} ({delta})",
                        callback_data=delta,
                    )
                    for delta in (-5, -4, -3)
                ],
                [
                    InlineKeyboardButton(
                        text=f"{(timestamp + timedelta(hours=-1)).strftime('%H:%M')} (-1)",
                        callback_data=-1,
                    ),
                    InlineKeyboardButton(
                        text=f"{timestamp.strftime('%H:%M')} (0)",
                        callback_data=0,
                    ),
                    InlineKeyboardButton(
                        text=f"{(timestamp + timedelta(hours=1)).strftime('%H:%M')} (+1)",
                        callback_data=1,
                    ),
                    InlineKeyboardButton(
                        text=f"{(timestamp + timedelta(hours=2)).strftime('%H:%M')} (+2)",
                        callback_data=2,
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=f"{(timestamp + timedelta(hours=3)).strftime('%H:%M')} (+3)",
                        callback_data=3,
                    ),
                    InlineKeyboardButton(
                        text=f"{(timestamp + timedelta(hours=4)).strftime('%H:%M')} (+4)",
                        callback_data=4,
                    ),
                    InlineKeyboardButton(
                        text=f"{(timestamp + timedelta(hours=5, minutes=30)).strftime('%H:%M')} "
                        f"(+5:30)",
                        callback_data=5.5,
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=f"{(timestamp + timedelta(hours=delta)).strftime('%H:%M')} "
                        f"(+{delta})",
                        callback_data=delta,
                    )
                    for delta in (8, 9, 10)
                ],
                [
                    InlineKeyboardButton(
                        text=f"{(timestamp + timedelta(hours=delta)).strftime('%H:%M')} "
                        f"(+{delta})",
                        callback_data=delta,
                    )
                    for delta in (11, 12, 13)
                ],
            ]
        ),
    )
    return State.TIME_SLOTS_START


async def ask_slots_for_one_day_or_teaching_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If this function is called for the first time in a conversation, **stores the timezone**
    and gives time slots for Monday.

    If this function is called after choosing time slots for a day, asks for time slots for the
    next day.

    If this is the last day, makes asks for the first language to learn/teach.
    """

    query = update.callback_query
    await query.answer()

    if re.match(r"^[+-]?\d{1,2}$", query.data):  # this is a UTC offset
        context.user_data.utc_offset = int(query.data)
        context.user_data.time_slots_for_day = defaultdict(list)

        # setting day of week to Monday.  This is temporary, so won't mix it with user_data
        context.chat_data["day_idx"] = 0

    elif query.data == CallbackData.NEXT:  # user pressed "next" button after choosing slots
        if context.chat_data["day_idx"] == 6:  # we have reached Sunday
            # TODO what if the user chose no slots at all?
            context.user_data.levels_for_teaching_language = {}
            # if the dictionary is empty, it means that no language was chosen yet.
            # In this case no "done" button must be shown.
            show_done_button = True if context.user_data.levels_for_teaching_language else False
            await CQReplySender.ask_teaching_languages(
                context, query, show_done_button=show_done_button
            )
            return State.TEACHING_LANGUAGE
        context.chat_data["day_idx"] += 1

    await CQReplySender.ask_with_time_slots(context, query)

    return State.TIME_SLOTS_MENU


async def save_one_time_slot_ask_another(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores one time slot and offers to choose another."""
    query = update.callback_query
    await query.answer()

    day = DAY_OF_WEEK_FOR_INDEX[context.chat_data["day_idx"]]
    context.user_data.time_slots_for_day[day].append(query.data)

    await CQReplySender.ask_with_time_slots(context, query)

    return State.TIME_SLOTS_MENU


async def save_teaching_language_ask_another_or_level_or_experience(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Saves teaching language, asks for level. If the user is a teacher and is done choosing
    levels, asks for more languages.

    If the user is a teacher and has finished choosing languages, asks about language of
    communication in class.
    """

    query = update.callback_query
    await query.answer()

    # for now students can only choose one language, so callback_data == "done" is only possible
    # for a teacher, but we'll keep it explicit here
    if query.data == CallbackData.DONE and context.user_data.role == Role.TEACHER:
        await CQReplySender.ask_student_communication_languages(context, query)
        return State.COMMUNICATION_LANGUAGE_IN_CLASS

    context.user_data.levels_for_teaching_language[query.data] = []

    await CQReplySender.ask_language_levels(context, query, show_done_button=False)
    return State.LEVEL


async def save_level_ask_level_for_next_language_or_communication_language(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Saves level, asks for another level of the language chosen (for teachers) or for
    communication language in groups (for students).
    """

    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.DONE:
        # A teacher has finished selecting levels for this language: ask for another language
        await CQReplySender.ask_teaching_languages(context, query)
        return State.TEACHING_LANGUAGE

    last_language_added = tuple(context.user_data.levels_for_teaching_language.keys())[-1]
    context.user_data.levels_for_teaching_language[last_language_added].append(query.data)

    logger.info(context.user_data.levels_for_teaching_language)

    # move on for a student (they can only choose one language and one level)
    if context.user_data.role == Role.STUDENT:
        await CQReplySender.ask_student_communication_languages(
            context,
            query,
        )
        return State.COMMUNICATION_LANGUAGE_IN_CLASS

    # Ask the teacher for another level of the same language
    await CQReplySender.ask_language_levels(context, query)
    return State.LEVEL


async def save_student_communication_language_start_test_or_ask_teaching_experience(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Saves communication language, starts test for a student (if the teaching language
    chosen was English) or asks teacher about teaching experience.
    """

    query = update.callback_query
    await query.answer()

    context.user_data.communication_language_in_class = query.data

    logger.info(context.user_data.communication_language_in_class)

    if context.user_data.role == Role.STUDENT:
        # start test
        return State.COMMENT  # TODO
    else:
        await CQReplySender.ask_yes_no(
            context, query, question_phrase_internal_id="ask_teacher_experience"
        )
        return State.NUMBER_OF_GROUPS_OR_FREQUENCY


async def save_prior_teaching_experience_ask_groups_or_frequency(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Saves information about teaching experience, asks for frequency (inexperienced teachers)
    or number of groups (for experienced teachers).
    """

    query = update.callback_query
    await query.answer()
    context.user_data.has_prior_teaching_experience = (
        True if query.data == CallbackData.YES else False
    )

    logger.info(f"Has teaching experience: {context.user_data.has_prior_teaching_experience}")

    if context.user_data.has_prior_teaching_experience:
        numbers_of_groups = (1, 2)

        buttons = [
            [
                InlineKeyboardButton(
                    PHRASES[f"option_number_of_groups_{number}"][context.user_data.locale],
                    callback_data=number,
                )
                for number in numbers_of_groups
            ]
        ]

        await query.edit_message_text(
            PHRASES["ask_teacher_number_of_groups"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return State.TEACHING_FREQUENCY
    else:
        await CQReplySender.ask_teaching_frequency(context, query)
        return State.PREFERRED_STUDENT_AGE_GROUPS_START


async def save_number_of_groups_ask_frequency(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """For experienced teachers: saves information about number of groups, asks for frequency
    (inexperienced teachers).
    """
    query = update.callback_query
    await query.answer()

    context.user_data.teacher_number_of_groups = query.data

    await CQReplySender.ask_teaching_frequency(context, query)
    return State.PREFERRED_STUDENT_AGE_GROUPS_START


async def save_frequency_ask_student_age_groups(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Saves frequency, asks for preferred age groups of students."""
    query = update.callback_query
    await query.answer()

    context.user_data.class_frequency = query.data
    context.user_data.teacher_age_groups_of_students = []

    await CQReplySender.ask_student_age_groups_for_teacher(context, query)

    return State.PREFERRED_STUDENT_AGE_GROUPS_MENU


async def save_student_age_group_ask_another(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Saves preferred age group of students, asks another."""
    query = update.callback_query
    await query.answer()

    if query.data == CallbackData.DONE:
        return State.COMMENT  # TODO

    context.user_data.teacher_age_groups_of_students.append(query.data)

    # TODO extract constant (all groups are selected)
    if len(context.user_data.teacher_age_groups_of_students) == 3:
        return State.COMMENT  # TODO

    await CQReplySender.ask_student_age_groups_for_teacher(context, query)

    return State.PREFERRED_STUDENT_AGE_GROUPS_MENU


async def bye(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the comment and ends the conversation."""

    logger.info(context.user_data.time_slots_for_day)
    await update.effective_chat.send_message("Thank you! I hope we can talk again some day.")
    return ConversationHandler.END


async def cancel(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Cancels and ends the conversation."""

    user = update.message.from_user

    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def send_help(update: Update, context: CUSTOM_CONTEXT_TYPES):
    """Displays help message."""

    await update.message.reply_text(
        "Enter /start to start the conversation!", reply_markup=ReplyKeyboardRemove()
    )


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it the bot's token.
    application = (
        Application.builder()
        .token(os.environ.get("TOKEN"))
        .context_types(ContextTypes(user_data=UserData))
        .build()
    )

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            State.IS_REGISTERED: [
                CallbackQueryHandler(save_interface_lang_ask_if_already_registered)
            ],
            State.FIRST_NAME_OR_BYE: [
                CallbackQueryHandler(redirect_to_coordinator_if_registered_ask_first_name)
            ],
            State.ROLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_first_name_ask_role)
            ],
            State.AGE: [CallbackQueryHandler(save_role_ask_age)],
            State.LAST_NAME: [CallbackQueryHandler(save_age_ask_last_name)],
            State.SOURCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_last_name_ask_source)
            ],
            State.CHECK_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_source_check_username)
            ],
            State.PHONE_NUMBER: [CallbackQueryHandler(save_username_ask_phone)],
            State.EMAIL: [
                MessageHandler(
                    (filters.CONTACT ^ filters.TEXT) & ~filters.COMMAND, save_phone_ask_email
                )
            ],
            State.TIMEZONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_email_ask_timezone)
            ],
            State.TIME_SLOTS_START: [
                CallbackQueryHandler(ask_slots_for_one_day_or_teaching_language)
            ],
            State.TIME_SLOTS_MENU: [
                CallbackQueryHandler(ask_slots_for_one_day_or_teaching_language, pattern="^next$"),
                CallbackQueryHandler(save_one_time_slot_ask_another),
            ],
            State.TEACHING_LANGUAGE: [
                CallbackQueryHandler(save_teaching_language_ask_another_or_level_or_experience),
            ],
            State.LEVEL: [
                CallbackQueryHandler(
                    save_level_ask_level_for_next_language_or_communication_language
                )
            ],
            State.COMMUNICATION_LANGUAGE_IN_CLASS: [
                CallbackQueryHandler(
                    save_student_communication_language_start_test_or_ask_teaching_experience
                )
            ],
            State.NUMBER_OF_GROUPS_OR_FREQUENCY: [
                CallbackQueryHandler(save_prior_teaching_experience_ask_groups_or_frequency)
            ],
            State.TEACHING_FREQUENCY: [CallbackQueryHandler(save_number_of_groups_ask_frequency)],
            State.PREFERRED_STUDENT_AGE_GROUPS_START: [
                CallbackQueryHandler(save_frequency_ask_student_age_groups)
            ],
            State.PREFERRED_STUDENT_AGE_GROUPS_MENU: [
                CallbackQueryHandler(save_student_age_group_ask_another)
            ],
            State.COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bye)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    help_handler = CommandHandler("help", send_help)
    application.add_handler(help_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
