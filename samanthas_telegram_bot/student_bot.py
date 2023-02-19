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

from samanthas_telegram_bot.constants import (
    DAY_OF_WEEK_FOR_INDEX,
    EMAIL_PATTERN,
    LANGUAGE_CODES,
    LEVEL_KEYBOARD,
    LOCALES,
    PHONE_PATTERN,
    PHRASES,
)
from samanthas_telegram_bot.custom_context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.inline_keyboards import (
    make_dict_for_inline_keyboard_with_languages,
    make_dict_for_inline_keyboard_with_time_slots,
)
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

    # TODO can we factor this out? This is tricky given that user's locale has to be respected
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    PHRASES["option_yes"][context.user_data.locale], callback_data="yes"
                ),
                InlineKeyboardButton(
                    PHRASES["option_no"][context.user_data.locale], callback_data="no"
                ),
            ]
        ]
    )

    await query.edit_message_text(
        text=PHRASES["confirm_language_of_conversation"][context.user_data.locale]
        + "\n"
        + PHRASES["ask_already_with_us"][context.user_data.locale],
        reply_markup=keyboard,
    )
    return State.FIRST_NAME_OR_BYE


async def redirect_to_coordinator_if_registered_ask_first_name(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """If user is already registered, redirect to coordinator. Otherwise, ask for first name."""

    query = update.callback_query
    await query.answer()

    if query.data == "yes":
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
                        text=PHRASES["option_student"][context.user_data.locale],
                        callback_data="student",
                    ),
                    InlineKeyboardButton(
                        text=PHRASES["option_teacher"][context.user_data.locale],
                        callback_data="teacher",
                    ),
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

    if context.user_data.role == "student":
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
        # TODO this is repeated above
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        PHRASES["option_yes"][context.user_data.locale], callback_data="yes"
                    ),
                    InlineKeyboardButton(
                        PHRASES["option_no"][context.user_data.locale], callback_data="no"
                    ),
                ]
            ]
        )

        await query.edit_message_text(
            PHRASES["ask_if_18"][context.user_data.locale],
            reply_markup=keyboard,
        )

    return State.LAST_NAME


async def save_age_ask_last_name(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """For students, stores age. For teachers, checks if they are above 18. Asks teachers above 18
    and all students to give their last name.
    """

    query = update.callback_query
    await query.answer()

    # end conversation for would-be teachers that are minors
    if context.user_data.role == "teacher" and query.data == "no":
        # TODO actual link to chat
        await query.edit_message_text(
            PHRASES["reply_under_18"][context.user_data.locale],
            reply_markup=InlineKeyboardMarkup([]),
        )
        return ConversationHandler.END

    if context.user_data.role == "student":
        context.user_data.age = query.data

    await query.edit_message_text(PHRASES["ask_last_name"][context.user_data.locale])
    return State.SOURCE


async def save_last_name_ask_source(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the last name and asks the user how they found out about Samantha's Group."""
    context.user_data.last_name = update.message.text
    await update.effective_chat.send_message(PHRASES["ask_source"][context.user_data.locale])
    return State.CHECK_USERNAME


async def save_source_check_username(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the source of knowledge about SSG, checks Telegram nickname or asks for
    phone number.
    """

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
                        for option in ("yes", "no")
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
            # TODO "-" for no email?
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
                        text=f"UTC-1 ({(timestamp + timedelta(hours=-1)).strftime('%H:%M')})",
                        callback_data=-1,
                    ),
                    InlineKeyboardButton(
                        text=f"UTC ({timestamp.strftime('%H:%M')})",
                        callback_data=0,
                    ),
                    InlineKeyboardButton(
                        text=f"UTC+1 ({(timestamp + timedelta(hours=1)).strftime('%H:%M')})",
                        callback_data=1,
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=f"UTC+2 ({(timestamp + timedelta(hours=2)).strftime('%H:%M')})",
                        callback_data=2,
                    ),
                    InlineKeyboardButton(
                        text=f"UTC+3 ({(timestamp + timedelta(hours=3)).strftime('%H:%M')})",
                        callback_data=3,
                    ),
                    InlineKeyboardButton(
                        text=f"UTC+4 ({(timestamp + timedelta(hours=4)).strftime('%H:%M')})",
                        callback_data=4,
                    ),
                ],
            ]
        ),
    )
    return State.TIME_SLOTS_START


async def ask_slots_for_one_day(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """If this function is called for the first time in a conversation, **stores the timezone**
    and gives time slots for Monday.

    If this function is called after choosing time slots for a day, asks for time slots for the
    next day.

    If this is the last day, makes a transition to the next conversation state.
    """

    query = update.callback_query
    await query.answer()

    if re.match(r"^[+-]?\d{1,2}$", query.data):  # this is a UTC offset
        # whether it's summer or winter timezone will be for the backend to decide
        context.user_data.utc_offset = int(query.data)
        context.user_data.time_slots_for_day = defaultdict(list)

        # setting day of week to Monday.  This is temporary, so won't mix it with user_data
        context.chat_data["day_idx"] = 0

    elif query.data == "next":  # this is user having pressed "next" button after choosing slots
        if context.chat_data["day_idx"] == 6:  # we have reached Sunday
            context.user_data.levels_for_teaching_language = {}
            # TODO what if the user chose no slots at all?
            await query.edit_message_text(**make_dict_for_inline_keyboard_with_languages(context))
            return State.TEACHING_LANGUAGE
        context.chat_data["day_idx"] += 1

    await query.edit_message_text(**make_dict_for_inline_keyboard_with_time_slots(context))

    return State.TIME_SLOTS_MENU


async def save_one_time_slot_ask_another(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores one time slot and offers to choose another."""
    query = update.callback_query
    await query.answer()

    day = DAY_OF_WEEK_FOR_INDEX[context.chat_data["day_idx"]]
    context.user_data.time_slots_for_day[day].append(query.data)

    await query.edit_message_text(**make_dict_for_inline_keyboard_with_time_slots(context))

    return State.TIME_SLOTS_MENU


async def save_teaching_language_ask_another(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Saves teaching language and, if the user is a teacher, asks for more languages."""

    query = update.callback_query
    await query.answer()

    if query.data == "done":
        await query.edit_message_text(
            "What is the level of?", reply_markup=InlineKeyboardMarkup([])
        )  # TODO
        return State.LEVEL

    # levels will be filled at next stage
    context.user_data.levels_for_teaching_language[query.data] = []

    if context.user_data.role == "student":
        # a student is only allowed to choose one language at the moment
        await query.edit_message_text(
            "What is the level of?", reply_markup=InlineKeyboardMarkup([])
        )  # TODO
        return State.LEVEL

    await query.edit_message_text(**make_dict_for_inline_keyboard_with_languages(context))
    return State.TEACHING_LANGUAGE


async def save_language_ask_level(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Asks for the level of the language chosen."""

    query = update.callback_query
    await query.answer()

    # list conforms to general approach that a person can potentially learn/teach many languages
    context.user_data.teaching_languages = [query.data]

    # I have to repeat this because of user's locale (can't define as global constant)
    # TODO maybe refactor to a function
    language_for_callback_data = {
        code: PHRASES[code][context.user_data.locale] for code in LANGUAGE_CODES
    }

    lang_name = language_for_callback_data[context.user_data.teaching_languages[0]]
    await query.edit_message_text(
        text=f"{PHRASES['ask_student_language_level'][context.user_data.locale]} *{lang_name}*?",
        reply_markup=LEVEL_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    return State.COMMENT  # TODO


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
            State.TEACHING_LANGUAGE: [CallbackQueryHandler(save_teaching_language_ask_another)],
            # State.LEVEL: [CallbackQueryHandler(save_language_ask_level)],
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
            State.TIME_SLOTS_START: [CallbackQueryHandler(ask_slots_for_one_day)],
            State.TIME_SLOTS_MENU: [
                CallbackQueryHandler(ask_slots_for_one_day, pattern="^next$"),
                CallbackQueryHandler(save_one_time_slot_ask_another),
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
