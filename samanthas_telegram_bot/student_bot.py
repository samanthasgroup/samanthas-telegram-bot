import logging
import os

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

LEVEL, HOW_OFTEN, CHOOSE_DAY, CHOOSE_TIME, CHOOSE_ANOTHER_DAY, COMMENT = range(6)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user about their gender."""

    reply_keyboard = [["English", "Ukrainian", "Russian"]]

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
    return LEVEL


async def level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected gender and asks for a photo."""

    context.user_data["language"] = update.message.text.lower()[:3]
    logger.info(f"Language interface: {context.user_data['language']}")
    logger.info(f"Chat ID: {update.effective_chat.id}")

    reply_keyboard = [["A0", "A1", "A2"], ["B1", "B2"], ["C1", "C2"], ["Don't know"]]

    await update.message.reply_text(
        "What is your level of English?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="What is your level?",
        ),
    )

    return HOW_OFTEN


async def how_often(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the photo and asks for a location."""

    reply_keyboard = [["1", "2", "3"]]

    await update.message.reply_text(
        "How many times a week do you wish to study?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="How many times?",
        ),
    )

    return CHOOSE_DAY


async def choose_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""

    if update.message.text.lower() == "no":
        await update.message.reply_text(
            "Great! Is there anything else you want to say?",
            reply_markup=ReplyKeyboardRemove(),
        )
        return COMMENT

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
    return CHOOSE_TIME


async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""

    context.user_data["days"].append(update.message.text)

    await update.message.reply_text(
        f"{update.message.text}: enter time range(s)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return CHOOSE_ANOTHER_DAY


async def choose_another_day_or_done(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Stores the location and asks for some info about the user."""

    context.user_data["time_slots"].append(update.message.text)

    reply_keyboard = [["Yes", "No"]]

    result = ",".join(
        f"{day} ({timing})"
        for day, timing in zip(
            context.user_data["days"], context.user_data["time_slots"]
        )
    )

    await update.message.reply_text(
        f"You have chosen:{result}. Choose another day or days?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Continue choosing?",
        ),
    )
    return CHOOSE_DAY


async def final_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the info about the user and ends the conversation."""

    user = update.message.from_user
    logger.info("Bio of %s: %s", user.first_name, update.message.text)

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
            LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level)],
            HOW_OFTEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, how_often)],
            CHOOSE_DAY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_day),
            ],
            CHOOSE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_time)],
            CHOOSE_ANOTHER_DAY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, choose_another_day_or_done
                ),
            ],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, final_comment)],
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
