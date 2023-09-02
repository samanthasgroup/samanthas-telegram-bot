import asyncio
import logging
import os
import traceback
import typing

import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from telegram import BotCommandScopeAllPrivateChats, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    TypeHandler,
    filters,
)

import samanthas_telegram_bot.conversation.callbacks.registration.common_main_flow as common_main
from samanthas_telegram_bot.auxil.constants import (
    ADMIN_CHAT_ID,
    BOT_OWNER_USERNAME,
    EXCEPTION_TRACEBACK_CLEANUP_PATTERN,
    LOGGING_LEVEL,
    WEBHOOK_PATH_FOR_CHATWOOT,
    WEBHOOK_PATH_FOR_TELEGRAM,
    WEBHOOK_URL_PREFIX,
)
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.conversation.auxil.conversation_handler import CONVERSATION_HANDLER
from samanthas_telegram_bot.conversation.callbacks.chat_with_helpdesk import MessageForwarder
from samanthas_telegram_bot.data_structures.context_types import (
    CUSTOM_CONTEXT_TYPES,
    BotData,
    ChatData,
    UserData,
)
from samanthas_telegram_bot.data_structures.custom_context import CustomContext
from samanthas_telegram_bot.data_structures.custom_updates import ChatwootUpdate
from samanthas_telegram_bot.data_structures.enums import LoggingLevel

load_dotenv()

logging_level = typing.cast(str, LOGGING_LEVEL)
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s | %(module)s (%(funcName)s:%(lineno)s)",
    level=getattr(logging, logging_level),
)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def error_handler(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
    """Logs the error and send a telegram message to notify the developer."""

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)

    tb_string = "".join(
        EXCEPTION_TRACEBACK_CLEANUP_PATTERN.sub("", item)
        for item in tb_list
        if "/virtualenvs/" not in item  # don't show traceback lines from external modules
    )
    tb_string = f"<code>{tb_string}</code>"

    if not isinstance(update, ChatwootUpdate) and update.message is not None:
        tb_string = (
            f"{tb_string}\n<strong>Message received from user</strong>: {update.message.text}\n"
        )
        # TODO this will not work for now because the user has to reply to the message,
        #  not just send his message after bot's.  This could be solved by ForceReply()
        #  as reply_markup where possible.
        if update.message.reply_to_message is not None:
            tb_string = (
                f"{tb_string}\n<strong>This was a reply to message from bot</strong>: "
                f"{update.message.reply_to_message.text}\n"
            )

    if not isinstance(update, ChatwootUpdate) and update.callback_query is not None:
        tb_string = (
            f"{tb_string}\n<strong>Message the user reacted to</strong> (first 100 chars):\n\n"
            f"{update.effective_message.text[:100]}...\n\n"
            f"<strong>Data from button pressed</strong>: {update.callback_query.data}\n"
        )

    await logs(
        bot=context.bot,
        update=update,
        level=LoggingLevel.EXCEPTION,
        text=(
            "Registration bot encountered an exception:"
            f"\n\n{tb_string}\n"
            f"@{BOT_OWNER_USERNAME}"
        ),
        parse_mode_for_admin_group_message=ParseMode.HTML,
        needs_to_notify_admin_group=True,
    )


async def post_init(application: Application) -> None:
    await application.bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
    await application.bot.set_my_commands(
        [
            ("start", "Start registration"),
            ("cancel", "Cancel registration"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="en",
    )
    await application.bot.set_my_commands(
        [
            ("start", "Начать регистрацию"),
            ("cancel", "Отменить регистрацию"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="ru",
    )
    await application.bot.set_my_commands(
        [
            ("start", "Почати реєстрацію"),
            ("cancel", "Перервати реєстрацію"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="ua",
    )

    await application.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text="Registration bot started",
        parse_mode=None,
    )


async def main() -> None:
    """Run the bot."""
    logging.getLogger(__name__)  # TODO remove

    # Set up webserver
    async def telegram(request: Request) -> Response:
        """Handle incoming Telegram updates by putting them into the `update_queue`"""
        await application.update_queue.put(
            Update.de_json(data=await request.json(), bot=application.bot)
        )
        return Response()

    async def custom_updates(request: Request) -> Response:
        """Put incoming webhook updates into the `update_queue`."""
        await application.update_queue.put(ChatwootUpdate(data=await request.json()))
        return Response()

    starlette_app = Starlette(
        routes=[
            Route(f"/{WEBHOOK_PATH_FOR_TELEGRAM}", telegram, methods=["POST"]),
            Route(f"/{WEBHOOK_PATH_FOR_CHATWOOT}", custom_updates, methods=["POST"]),
        ],
    )
    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=starlette_app,
            port=5000,
            use_colors=False,
            host="127.0.0.1",
        )
    )

    context_types = ContextTypes(
        context=CustomContext, user_data=UserData, chat_data=ChatData, bot_data=BotData
    )

    # Create the Application and pass it the token.
    persistence = PicklePersistence(filepath="bot_persistence.pickle", context_types=context_types)

    application = (
        Application.builder()
        .token(os.environ.get("BOT_TOKEN"))
        .persistence(persistence)
        # Here we set updater to None because we want our custom webhook server to handle
        # the updates and hence we don't need an Updater instance
        .updater(None)
        .context_types(context_types)
        .build()
    )

    # register handlers
    # TODO add filter for private chats (not group chats) only
    application.add_handler(CONVERSATION_HANDLER)
    application.add_handler(CommandHandler("help", common_main.send_help))
    application.add_handler(
        # use strict=True to be able to use custom context
        TypeHandler(
            type=ChatwootUpdate, callback=MessageForwarder.from_helpdesk_to_user, strict=True
        )
    )
    # TODO add callback to either check communication mode or catch Chatwoot exception
    #  if conversation ID is not found
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, MessageForwarder.from_user_to_helpdesk)
    )
    application.add_error_handler(error_handler)

    # Pass webhook settings to telegram
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL_PREFIX}{WEBHOOK_PATH_FOR_TELEGRAM}",
        secret_token=os.environ.get("TELEGRAM_WEBHOOK_SECRET_TOKEN"),
        allowed_updates=Update.ALL_TYPES,
    )

    # Run application and webserver together
    async with application:
        # since we're no longer using run_polling() or start_webhook(),
        # we have to call `post_init` here explicitly, otherwise it won't be executed
        await post_init(application)
        await application.start()
        await webserver.serve()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
