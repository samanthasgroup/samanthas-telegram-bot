import logging
import os
import re
from dataclasses import dataclass
from datetime import timedelta
from enum import IntEnum, auto
from typing import Any

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
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    ExtBot,
    MessageHandler,
    filters,
)

from data.read_phrases import read_phrases

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"^([\w\-.]+)@([\w\-.]+)\.([a-zA-Z]{2,5})$")

# TODO maybe factor out from phrases; addition of language will require double changes
LANGUAGE_CODES = ("en", "fr", "de", "es", "it", "pl", "cz", "se")

LEVELS = ("A0", "A1", "A2", "B1", "B2", "C1", "C2")
LEVEL_BUTTONS = tuple(InlineKeyboardButton(text=item, callback_data=item) for item in LEVELS)
LEVEL_KEYBOARD = InlineKeyboardMarkup([LEVEL_BUTTONS[:3], LEVEL_BUTTONS[3:]])

LOCALES = ("ua", "en", "ru")
PHRASES = read_phrases()


@dataclass
class UserData:
    locale: str = None
    first_name: str = None
    last_name: str = None
    age: str = None  # it will be an age range
    username: str = None
    phone_number: str = None
    email: str = None
    teaching_languages: list = None
    days: list = None
    time_slots: list = None


# include the custom class into ContextTypes to get attribute hinting
# (replacing standard dict with UserData for "user_data")
CUSTOM_CONTEXT_TYPES = CallbackContext[ExtBot[None], UserData, dict[Any, Any], dict[Any, Any]]


class State(IntEnum):
    """Provides integer keys for the dictionary of states for ConversationHandler."""

    IS_REGISTERED = auto()
    FIRST_NAME_OR_BYE = auto()
    AGE = auto()
    LANGUAGE_TO_LEARN = auto()
    LEVEL = auto()
    CHECK_USERNAME = auto()
    PHONE_NUMBER = auto()
    EMAIL = auto()
    TIMEZONE = auto()
    HOW_OFTEN = auto()
    CHOOSE_DAY = auto()
    CHOOSE_TIME = auto()
    CHOOSE_ANOTHER_DAY = auto()
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
    return State.AGE


async def save_first_name_ask_age(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the full name and asks the user what their age is."""

    context.user_data.first_name = update.message.text

    ages = [
        ["6-8", "9-11", "12-14", "15-17"],
        ["18-20", "21-25", "26-30", "31-35"],
        ["36-40", "41-45", "46-50", "51-55"],
        ["56-60", "61-65", "66-70", "71-75"],
        ["76-80", "81-65", "86-90", "91-95"],
    ]

    rows_of_buttons = [
        [InlineKeyboardButton(text, callback_data=text) for text in row] for row in ages
    ]

    await update.message.reply_text(
        PHRASES["ask_age"][context.user_data.locale],
        reply_markup=InlineKeyboardMarkup(rows_of_buttons),
    )
    return State.LANGUAGE_TO_LEARN


async def save_age_ask_language(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the age and asks the user what language they want to learn."""
    query = update.callback_query
    await query.answer()

    context.user_data.age = query.data

    language_for_callback_data = {
        code: PHRASES[code][context.user_data.locale] for code in LANGUAGE_CODES
    }

    language_buttons = tuple(
        InlineKeyboardButton(text=value, callback_data=key)
        for key, value in language_for_callback_data.items()
    )

    await query.edit_message_text(
        PHRASES["ask_language_to_learn"][context.user_data.locale],
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([language_buttons[:4], language_buttons[4:]]),
    )
    return State.LEVEL


# # SAVING FOR TEACHER's BOT
# async def save_language_ask_another(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
#     """Saves the first language to learn, asks for second one.
#     The student is only allowed to study maximum two languages at the moment.
#     """
#     query = update.callback_query
#     await query.answer()
#
#     context.user_data.teaching_languages.append(query.data)
#
#     if len(context.user_data.teaching_languages) == 2:
#         # check the level of 2nd language chosen
#         await query.edit_message_text(
#             f"That's it, you can only choose two languages 😉\nWhat is your level of "
#             f"*{LANGUAGE_FOR_CALLBACK_DATA[query.data]}*?",
#             reply_markup=LEVEL_KEYBOARD,
#             parse_mode=ParseMode.MARKDOWN_V2,
#         )
#         return State.LEVEL
#
#     buttons_left = tuple(
#        b for b in LANGUAGE_BUTTONS if b.callback_data not in context.user_data.teaching_languages
#     )
#
#     await query.edit_message_text(
#         # the message is the same for it to look like an interactive menu
#         "What languages would you like to learn?",
#         reply_markup=InlineKeyboardMarkup(
#             [
#                 buttons_left[:4],
#                 buttons_left[4:],
#                 [InlineKeyboardButton(text="Done", callback_data="ok")],
#             ]
#         ),
#     )
#     return State.LANGUAGE_MENU


async def save_language_ask_level(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Asks for the level of the language chosen."""

    query = update.callback_query
    await query.answer()

    # a list conforms to general approach that a person can potentially learn/teach many languages
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

    return State.CHECK_USERNAME


async def save_level_check_username(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the selected level, checks Telegram nickname or asks for phone number."""

    query = update.callback_query
    await query.answer()

    # TODO
    # context.user_data.language_level = query.data

    username = update.effective_user.username

    if username:
        await query.edit_message_text(
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

    logger.info(f"Languages to learn: {context.user_data.teaching_languages}")

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

    logger.info(f"Phone: {update.message.contact.phone_number}")

    # if user passed their contact, record phone number and proceed
    if update.message.contact.phone_number:
        context.user_data.phone_number = update.message.contact.phone_number

        await update.message.reply_text(
            PHRASES["ask_email"][context.user_data.locale],
            reply_markup=ReplyKeyboardRemove(),
        )

        return State.TIMEZONE

    # checking this, not update.effective_user.username
    if not context.user_data.username:
        if not update.message.text:  # TODO validate; text cannot be empty anyway
            await update.message.reply_text(
                PHRASES["invalid_phone_number"][context.user_data.locale],
                reply_markup=ReplyKeyboardRemove(),
            )
            return State.EMAIL

    if update.message.text:
        context.user_data.phone_number = update.message.text  # TODO validate
        await update.message.reply_text(
            PHRASES["ask_email"][context.user_data.locale],
            reply_markup=ReplyKeyboardRemove(),
        )
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
                        text=f"UTC-1 ({(timestamp - timedelta(hours=1)).strftime('%H:%M')})",
                        callback_data="UTC-1",
                    ),
                    InlineKeyboardButton(
                        text=f"UTC ({timestamp.strftime('%H:%M')})",
                        callback_data="UTC",
                    ),
                    InlineKeyboardButton(
                        text=f"UTC+1 ({(timestamp + timedelta(hours=1)).strftime('%H:%M')})",
                        callback_data="UTC+1",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=f"UTC+2 ({(timestamp + timedelta(hours=2)).strftime('%H:%M')})",
                        callback_data="UTC+2",
                    ),
                    InlineKeyboardButton(
                        text=f"UTC+3 ({(timestamp + timedelta(hours=3)).strftime('%H:%M')})",
                        callback_data="UTC+3",
                    ),
                    InlineKeyboardButton(
                        text=f"UTC+4 ({(timestamp + timedelta(hours=4)).strftime('%H:%M')})",
                        callback_data="UTC+4",
                    ),
                ],
            ]
        ),
    )
    return State.HOW_OFTEN


async def save_timezone_ask_how_often(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the timezone and asks how often user wants to study."""
    # TODO record either summer or winter timezone
    query = update.callback_query
    logger.info(query.data)
    await query.answer()
    await query.edit_message_text(text=f"Your timezone: {query.data}")

    await update.effective_chat.send_message(
        "How many times a week do you wish to study?",
        reply_markup=ReplyKeyboardMarkup(
            [["1", "2", "3"]],
            one_time_keyboard=True,
            input_field_placeholder="How many times?",
        ),
    )

    return State.CHOOSE_DAY


async def save_how_often_ask_day(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Saves how often, asks for the day(s)."""

    # TODO save how often; loop for the given number of days?

    if update.message.text.lower() == "no":
        await update.message.reply_text(
            "Great! Is there anything else you want to say?",
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.COMMENT

    reply_keyboard = [
        ["All weekdays", "Weekend"],
        ["Monday", "Tuesday", "Wednesday"],
        ["Thursday", "Friday"],
        ["Saturday", "Sunday"],
    ]

    await update.message.reply_text(
        "Choose day or days",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Choose day(s)",
        ),
    )
    return State.CHOOSE_TIME


async def save_day_ask_time(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the day and asks for time slots."""

    context.user_data.days.append(update.message.text)

    # TODO slots (how to choose multiple?)

    await update.effective_chat.send_message(
        "Choose a time slot",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    # TODO store in database with timezone correction?
                    #  How about daylight saving time?
                    InlineKeyboardButton(text="08:00-11:00", callback_data="8-11"),
                    InlineKeyboardButton(text="11:00-14:00", callback_data="11-14"),
                ],
                [
                    InlineKeyboardButton(text="14:00-17:00", callback_data="14-17"),
                    InlineKeyboardButton(text="17:00-21:00", callback_data="17-21"),
                ],
            ]
        ),
    )
    return State.CHOOSE_ANOTHER_DAY


async def save_time_choose_another_day_or_done(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> int:
    """Saves time slot, asks if user wants to choose another day."""

    query = update.callback_query
    logger.info(query.data)
    await query.answer()
    await query.edit_message_text(text=f"{query.data}")

    context.user_data.time_slots.append(query.data)

    reply_keyboard = [["Yes", "No"]]

    result = ",".join(
        f"{day} ({timing})"
        for day, timing in zip(context.user_data.days, context.user_data.time_slots)
    )

    await update.effective_chat.send_message(
        f"You have chosen:{result}. Choose another day or days?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Continue choosing?",
        ),
    )
    return State.CHOOSE_DAY


async def final_comment(update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
    """Stores the info about the user and ends the conversation."""

    user = update.message.from_user
    logger.info("Comment from %s: %s", user.first_name, update.message.text)

    await update.message.reply_text("Thank you! I hope we can talk again some day.")

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
                CallbackQueryHandler(
                    save_interface_lang_ask_if_already_registered, pattern="^(ru)|(ua)|(en)$"
                )
            ],
            State.FIRST_NAME_OR_BYE: [
                CallbackQueryHandler(
                    redirect_to_coordinator_if_registered_ask_first_name, pattern="^(yes)|(no)$"
                )
            ],
            State.AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_first_name_ask_age)],
            State.LANGUAGE_TO_LEARN: [
                # name can contain multiple words (hyphens are possible in them) with spaces
                CallbackQueryHandler(save_age_ask_language, pattern=r"^(\s*[\w-]+\s*)+$")
            ],
            State.LEVEL: [CallbackQueryHandler(save_language_ask_level, pattern=r"^.{2}$")],
            State.CHECK_USERNAME: [
                CallbackQueryHandler(save_level_check_username, pattern=r"^\w\d$")
            ],
            State.PHONE_NUMBER: [
                CallbackQueryHandler(save_username_ask_phone, pattern="^store_username_.+$")
            ],
            State.EMAIL: [
                MessageHandler(
                    (filters.CONTACT ^ filters.TEXT) & ~filters.COMMAND, save_phone_ask_email
                )
            ],
            State.TIMEZONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_email_ask_timezone)
            ],
            State.HOW_OFTEN: [CallbackQueryHandler(save_timezone_ask_how_often, pattern="UTC")],
            State.CHOOSE_DAY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_how_often_ask_day)
            ],
            State.CHOOSE_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_day_ask_time)
            ],
            State.CHOOSE_ANOTHER_DAY: [
                CallbackQueryHandler(
                    save_time_choose_another_day_or_done, pattern=r"\d{1,2}-\d{2}"
                ),
            ],
            State.COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, final_comment)],
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
