import asyncio
import logging
import os
import traceback
import typing
from dataclasses import dataclass

import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from telegram import BotCommandScopeAllPrivateChats, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, TypeHandler

import samanthas_telegram_bot.conversation.callbacks.registration.common_main_flow as common_main
from samanthas_telegram_bot.auxil.constants import ADMIN_CHAT_ID, BOT_OWNER_USERNAME, LOGGING_LEVEL
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.conversation.auxil.conversation_handler import (
    REGISTRATION_CONVERSATION_HANDLER,
)
from samanthas_telegram_bot.data_structures.constants import (
    BOT_URL_PATH_FOR_CHATWOOT_WEBHOOK,
    BOT_URL_PATH_FOR_TELEGRAM_WEBHOOK,
    EXCEPTION_TRACEBACK_CLEANUP_PATTERN,
    WEBHOOK_URL_PREFIX,
)
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import LoggingLevel

load_dotenv()

logging_level = typing.cast(str, LOGGING_LEVEL)
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s | %(module)s (%(funcName)s:%(lineno)s)",
    level=getattr(logging, logging_level),
)
logging.getLogger("httpx").setLevel(logging.WARNING)


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


async def error_handler(update: Update, context: CUSTOM_CONTEXT_TYPES) -> None:
    """Logs the error and send a telegram message to notify the developer."""

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)

    tb_string = "".join(
        EXCEPTION_TRACEBACK_CLEANUP_PATTERN.sub("", item)
        for item in tb_list
        if "/virtualenvs/" not in item  # don't show traceback lines from external modules
    )
    tb_string = f"<code>{tb_string}</code>"

    if update.message is not None:
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

    if update.callback_query is not None:
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


@dataclass
class WebhookUpdate:
    """Simple dataclass to wrap a custom update type"""

    data: str


class CustomContext(CUSTOM_CONTEXT_TYPES):  # type:ignore[misc]
    """
    Custom CallbackContext class that makes `user_data` available for updates of type
    `WebhookUpdate`.
    """

    @classmethod
    def from_update(
        cls,
        update: object,
        application: "Application",
    ) -> "CustomContext":
        if isinstance(update, WebhookUpdate):
            return cls(update.data)
        return super().from_update(update, application)


async def webhook_update(update: WebhookUpdate, context: CUSTOM_CONTEXT_TYPES) -> None:
    """Callback that handles the custom updates."""
    await context.bot.send_message(
        chat_id=context.user_data.chat_id, text=update.data, parse_mode=None
    )


async def main() -> None:
    """Run the bot."""

    # Set up webserver
    async def telegram(request: Request) -> Response:
        """Handle incoming Telegram updates by putting them into the `update_queue`"""
        await application.update_queue.put(
            Update.de_json(data=await request.json(), bot=application.bot)
        )
        return Response()

    async def custom_updates(request: Request) -> PlainTextResponse:
        """
        Handle incoming webhook updates by also putting them into the `update_queue` if
        the required parameters were passed correctly.
        """
        # TODO come check of data passed by Chatwoot

        await application.update_queue.put(WebhookUpdate(data=await request.json()))
        return PlainTextResponse("Thank you for the submission! It's being forwarded.")

    starlette_app = Starlette(
        routes=[
            Route(f"/{BOT_URL_PATH_FOR_TELEGRAM_WEBHOOK}", telegram, methods=["POST"]),
            Route(f"/{BOT_URL_PATH_FOR_CHATWOOT_WEBHOOK}", custom_updates, methods=["POST"]),
        ]
    )
    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=starlette_app,
            port=5000,
            use_colors=False,
            host="127.0.0.1",
        )
    )

    ContextTypes(context=CustomContext)

    # Create the Application and pass it the bot's token.
    application = (
        Application.builder()
        .token(os.environ.get("BOT_TOKEN"))
        # Here we set updater to None because we want our custom webhook server to handle
        # the updates and hence we don't need an Updater instance
        .updater(None)
        .context_types(ContextTypes(context=CustomContext))
        .post_init(post_init)
        .build()
    )

    # register handlers
    application.add_handler(REGISTRATION_CONVERSATION_HANDLER)
    application.add_handler(CommandHandler("help", common_main.send_help))
    application.add_error_handler(error_handler)

    # handler for updates from Chatwoot
    application.add_handler(TypeHandler(type=WebhookUpdate, callback=webhook_update))

    # Pass webhook settings to telegram
    await application.bot.set_webhook(
        listen="127.0.0.1",
        port=5000,
        url_path=BOT_URL_PATH_FOR_TELEGRAM_WEBHOOK,
        secret_token=os.environ.get("TELEGRAM_WEBHOOK_SECRET_TOKEN"),
        webhook_url=f"{WEBHOOK_URL_PREFIX}{BOT_URL_PATH_FOR_TELEGRAM_WEBHOOK}",
    )

    # Run application and webserver together
    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
