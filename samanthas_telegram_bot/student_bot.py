import logging
import os
import re
from datetime import timedelta
from enum import IntEnum, auto

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"^([\w\-.]+)@([\w\-.]+)\.([a-zA-Z]{2,5})$")

LANGUAGES = {
    "English": "en",
    "French": "fr",
    "German": "de",
    "Spanish": "sp",
    "Italian": "it",
    "Polish": "pl",
    "Czech": "cz",
    "Swedish": "se",
}

LANGUAGE_BUTTONS = tuple(
    InlineKeyboardButton(text=key, callback_data=value) for key, value in LANGUAGES.items()
)

LEVELS = ("A0", "A1", "A2", "B1", "B2", "C1", "C2")
LEVEL_BUTTONS = tuple(InlineKeyboardButton(text=item, callback_data=item) for item in LEVELS)
LEVEL_KEYBOARD = InlineKeyboardMarkup([LEVEL_BUTTONS[:3], LEVEL_BUTTONS[3:]])


class State(IntEnum):
    """Provides integer keys for the dictionary of states for ConversationHandler."""

    FULL_NAME = auto()
    AGE = auto()
    LANGUAGE_TO_LEARN = auto()
    LANGUAGE_MENU = auto()
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user about the language they want to communicate in."""

    logger.info(f"Chat ID: {update.effective_chat.id}")

    context.user_data["days"] = []
    context.user_data["time_slots"] = []

    await update.message.reply_text(
        f"Hi {update.message.from_user.first_name}! Please choose your language. "
        "Send /cancel to stop talking to me.\n\n",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Ukrainian",
                        callback_data="ukr",
                    ),
                    InlineKeyboardButton(
                        text="Russian",
                        callback_data="rus",
                    ),
                ],
            ]
        ),
    )

    return State.FULL_NAME


async def save_interface_lang_ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the interface language and asks the user what their name is."""

    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Thank you", reply_markup=InlineKeyboardMarkup([]))

    context.user_data["interface_language"] = query.data

    await update.effective_chat.send_message(
        "What's your full name that will be stored in our database?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return State.AGE


async def save_name_ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the full name and asks the user what their age is."""

    context.user_data["full_name_indicated_by_user"] = update.message.text

    await update.message.reply_text("What's your age?", reply_markup=ReplyKeyboardRemove())
    return State.LANGUAGE_TO_LEARN


async def save_age_ask_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the age and asks the user what language they want to learn."""
    context.user_data["language_to_learn"] = []

    try:
        context.user_data["age"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "Hmm... that doesn't look like a number. Please try again.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.LANGUAGE_TO_LEARN

    await update.message.reply_text(
        "What languages would you like to learn?",
        reply_markup=InlineKeyboardMarkup([LANGUAGE_BUTTONS[:4], LANGUAGE_BUTTONS[4:]]),
    )
    return State.LANGUAGE_MENU


async def save_language_ask_another(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the first language to learn, asks for second one.
    The student is only allowed to study maximum two languages at the moment.
    """
    query = update.callback_query
    await query.answer()

    context.user_data["language_to_learn"].append(query.data)

    if len(context.user_data["language_to_learn"]) == 2:
        await query.edit_message_text(
            "That's it, you can only choose two languages :) What is your level?",
            reply_markup=LEVEL_KEYBOARD,
        )

        return State.CHECK_USERNAME

    buttons_left = tuple(
        b
        for b in LANGUAGE_BUTTONS
        if b.callback_data not in context.user_data["language_to_learn"]
    )

    await query.edit_message_text(
        # the message is the same for it to look like an interactive menu
        "What languages would you like to learn?",
        reply_markup=InlineKeyboardMarkup(
            [
                buttons_left[:4],
                buttons_left[4:],
                [InlineKeyboardButton(text="Done", callback_data="ok")],
            ]
        ),
    )
    return State.LANGUAGE_MENU


async def save_language_ask_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected language to learn and asks for the level (if it's English)."""

    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Got it!", reply_markup=InlineKeyboardMarkup([]))

    # TODO as for each language
    await update.effective_chat.send_message("What is your level?", reply_markup=LEVEL_KEYBOARD)

    return State.CHECK_USERNAME


async def save_level_check_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected level, checks Telegram nickname or asks for phone number."""

    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=query.data, reply_markup=InlineKeyboardMarkup([]))
    context.user_data["language_level"] = query.data

    username = update.effective_user.username

    if username:
        await update.effective_chat.send_message(
            f"We will store your username @{username} to contact you the future. Is it OK?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Yes", callback_data="store_username_yes"),
                        InlineKeyboardButton(
                            text="No, I'll use another phone", callback_data="store_username_no"
                        ),
                    ],
                ]
            ),
        )

    return State.PHONE_NUMBER


async def save_username_ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """If user's username was empty or they chose to provide a phone number, ask for it."""

    logger.info(f"Languages to learn: {context.user_data['language_to_learn']}")

    username = update.effective_user.username

    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Thanks", reply_markup=InlineKeyboardMarkup([]))

    if query.data == "store_username_yes" and username:
        context.user_data["username"] = username
        logger.info(f"Username: {username}. Will be stored in the database.")
        await update.effective_chat.send_message(
            # TODO "-" for no email?
            "Please provide an email so that we can contact you",
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.TIMEZONE

    # TODO ReplyKeyboardMarkup([[KeyboardButton(text="Share", request_contact=True)]]
    context.user_data["username"] = None
    await update.effective_chat.send_message(
        "Please provide a phone number so that we can contact you",
        reply_markup=ReplyKeyboardRemove(),
    )

    return State.EMAIL


async def save_phone_ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the phone number and asks for email."""

    logger.info(f"Phone: {update.message.text}")

    # checking this, not update.effective_user.username
    if not context.user_data["username"]:
        context.user_data["phone_number"] = update.message.text
        if not update.message.text:  # TODO validate; text cannot be empty anyway
            await update.message.reply_text(
                "Please provide a valid phone number",
                reply_markup=ReplyKeyboardRemove(),
            )
            return State.EMAIL

    if update.message.text:
        context.user_data["phone_number"] = update.message.text  # TODO validate
        await update.message.reply_text(
            "Please provide your email",
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.TIMEZONE


async def save_email_ask_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the email and asks for timezone."""

    email = update.message.text.strip()
    if not EMAIL_PATTERN.match(email):
        await update.message.reply_text(
            "Please provide a valid email",
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.TIMEZONE
    context.user_data["email"] = email

    timestamp = update.message.date

    await update.message.reply_text(
        "What's your timezone? (Choose the correct current time)",
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


async def save_timezone_ask_how_often(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the timezone and asks how often user wants to study."""
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


async def save_how_often_ask_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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


async def save_day_ask_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the day and asks for time slots."""

    context.user_data["days"].append(update.message.text)

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
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Saves time slot, asks if user wants to choose another day."""

    query = update.callback_query
    logger.info(query.data)
    await query.answer()
    await query.edit_message_text(text=f"{query.data}")

    context.user_data["time_slots"].append(query.data)

    reply_keyboard = [["Yes", "No"]]

    result = ",".join(
        f"{day} ({timing})"
        for day, timing in zip(context.user_data["days"], context.user_data["time_slots"])
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


async def final_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the info about the user and ends the conversation."""

    user = update.message.from_user
    logger.info("Comment from %s: %s", user.first_name, update.message.text)

    await update.message.reply_text("Thank you! I hope we can talk again some day.")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""

    user = update.message.from_user

    logger.info("User %s canceled the conversation.", user.first_name)

    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def send_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays help message."""

    await update.message.reply_text(
        "Enter /start to start the conversation!", reply_markup=ReplyKeyboardRemove()
    )


def main() -> None:
    """Run the bot."""

    # Create the Application and pass it the bot's token.
    application = Application.builder().token(os.environ.get("TOKEN")).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            State.FULL_NAME: [
                CallbackQueryHandler(save_interface_lang_ask_name, pattern="^(rus)|(ukr)$")
            ],
            State.AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name_ask_age)],
            State.LANGUAGE_TO_LEARN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_age_ask_language)
            ],
            State.LANGUAGE_MENU: [
                # first check if user finished selecting the languages, if not - show menu again
                CallbackQueryHandler(save_language_ask_level, pattern=r"^ok$"),
                CallbackQueryHandler(save_language_ask_another, pattern=r"^\w{2}$"),
            ],
            State.LEVEL: [CallbackQueryHandler(save_language_ask_level, pattern=r"^\w{2}$")],
            State.CHECK_USERNAME: [
                CallbackQueryHandler(save_level_check_username, pattern=r"^\w\d$")
            ],
            State.PHONE_NUMBER: [
                CallbackQueryHandler(save_username_ask_phone, pattern="^store_username_.+$")
            ],
            State.EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_phone_ask_email)],
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
