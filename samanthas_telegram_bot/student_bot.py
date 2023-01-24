import logging
import os
from enum import IntEnum, auto

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
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


class State(IntEnum):
    """Provides integer keys for the dictionary of states for ConversationHandler."""

    FULL_NAME = auto()
    AGE = auto()
    LANGUAGE_TO_LEARN = auto()
    LEVEL = auto()
    CHECK_USERNAME = auto()
    GET_PHONE_NUMBER = auto()
    GET_EMAIL = auto()
    HOW_OFTEN = auto()
    CHOOSE_DAY = auto()
    CHOOSE_TIME = auto()
    CHOOSE_ANOTHER_DAY = auto()
    COMMENT = auto()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user about the language they want to communicate in."""

    reply_keyboard = [["Ukrainian", "Russian"]]

    context.user_data["days"] = []
    context.user_data["time_slots"] = []

    await update.message.reply_text(
        f"Hi {update.message.from_user.first_name}! Please choose your language. "
        "Send /cancel to stop talking to me.\n\n",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Choose your language",
        ),
    )
    logger.info(f"Chat ID: {update.effective_chat.id}")
    return State.FULL_NAME


async def full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the interface language and asks the user what their name is."""

    context.user_data["interface_language"] = update.message.text.lower()[:3]
    logger.info(f"Language of interface: {context.user_data['interface_language']}")

    await update.message.reply_text(
        "What's your full name that will be stored in our database?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return State.AGE


async def age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the full name and asks the user what their age is."""

    context.user_data["full_name_indicated_by_user"] = update.message.text

    await update.message.reply_text("What's your age?", reply_markup=ReplyKeyboardRemove())
    return State.LANGUAGE_TO_LEARN


async def language_to_learn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the full name and asks the user what language they want to learn."""

    try:
        context.user_data["age"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "Hmm... that doesn't look like a number. Please try again.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.LANGUAGE_TO_LEARN

    await update.message.reply_text(
        "What language do you want to learn?",
        reply_markup=ReplyKeyboardMarkup(
            [["English", "German", "Swedish", "Spanish"]],
            one_time_keyboard=True,
            input_field_placeholder="What language do you want to learn?",
        ),
    )
    return State.LEVEL


async def level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected language to learn and asks for the level (if it's English)."""

    # TODO since the interface will be multilingual, we'll have to resolve this text to an ID
    #  of language
    context.user_data["language_to_learn"] = update.message.text
    logger.info(f"Language to learn: {context.user_data['language_to_learn']}")

    reply_keyboard = [["A0", "A1", "A2"], ["B1", "B2"], ["C1", "C2"], ["Don't know"]]

    await update.message.reply_text(
        "What is your level of English?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="What is your level?",
        ),
    )

    return State.CHECK_USERNAME


async def check_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected level, checks Telegram nickname or asks for phone number."""

    context.user_data["language_level"] = update.message.text
    logger.info(f"Level: {context.user_data['language_level']}")

    username = update.effective_user.username

    if username:
        await update.message.reply_text(
            f"We will store your username @{username} to contact you the future. Is it OK?",
            reply_markup=ReplyKeyboardMarkup(
                [["OK!", "No, I'll provide a phone number"]],
                one_time_keyboard=True,
                input_field_placeholder="OK to use your Telegram username?",
            ),
        )

    return State.GET_PHONE_NUMBER


async def get_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """If user's username was empty or they chose to provide a phone number, ask for it."""

    username = update.effective_user.username

    if update.message.text == "OK!" and username:
        context.user_data["username"] = username
        logger.info(f"Username: {username}. Will be stored in the database.")
        await update.message.reply_text(
            # TODO "-" for no email?
            "Please provide an email so that we can contact you",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        context.user_data["username"] = None
        await update.message.reply_text(
            "Please provide a phone number so that we can contact you",
            reply_markup=ReplyKeyboardRemove(),
        )

    return State.GET_EMAIL


async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the phone number and asks for email."""

    # checking this, not update.effective_user.username
    if not context.user_data["username"]:
        context.user_data["phone_number"] = update.message.text
        if not update.message.text:  # TODO validate; text cannot be empty anyway
            await update.message.reply_text(
                "Please provide a valid phone number",
                reply_markup=ReplyKeyboardRemove(),
            )
            return State.GET_EMAIL

    if update.message.text:
        context.user_data["phone_number"] = update.message.text  # TODO validate
        await update.message.reply_text(
            "Please provide your email",
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.HOW_OFTEN


async def how_often(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the email and asks how many times student wants to study."""
    if not update.message.text:  # TODO validate (message can't be empty anyway)
        await update.message.reply_text(
            "Please provide a valid email",
            reply_markup=ReplyKeyboardRemove(),
        )
        return State.HOW_OFTEN

    await update.message.reply_text(
        "How many times a week do you wish to study?",
        reply_markup=ReplyKeyboardMarkup(
            [["1", "2", "3"]],
            one_time_keyboard=True,
            input_field_placeholder="How many times?",
        ),
    )

    return State.CHOOSE_DAY


async def choose_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""

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


async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""

    context.user_data["days"].append(update.message.text)

    await update.message.reply_text(
        f"{update.message.text}: enter time range(s)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return State.CHOOSE_ANOTHER_DAY


async def choose_another_day_or_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""

    context.user_data["time_slots"].append(update.message.text)

    reply_keyboard = [["Yes", "No"]]

    result = ",".join(
        f"{day} ({timing})"
        for day, timing in zip(context.user_data["days"], context.user_data["time_slots"])
    )

    await update.message.reply_text(
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
            State.FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, full_name)],
            State.AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            State.LANGUAGE_TO_LEARN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, language_to_learn)
            ],
            State.LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level)],
            State.CHECK_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_username)
            ],
            State.GET_PHONE_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone_number)
            ],
            State.GET_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            State.HOW_OFTEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, how_often)],
            State.CHOOSE_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_day)],
            State.CHOOSE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_time)],
            State.CHOOSE_ANOTHER_DAY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_another_day_or_done),
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
