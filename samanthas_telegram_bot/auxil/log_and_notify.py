import os
from logging import Logger

from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.enums import LoggingLevel

load_dotenv()


async def log_and_notify(
    bot: Bot,
    logger: Logger,
    level: LoggingLevel,
    text: str,
    needs_to_notify_admin_group: bool = True,
    parse_mode_for_admin_group_message: ParseMode | None = None,
) -> None:
    getattr(logger, level)(text)
    if needs_to_notify_admin_group:
        await notify_admins(bot=bot, text=text, parse_mode=parse_mode_for_admin_group_message)


async def notify_admins(bot: Bot, text: str, parse_mode: ParseMode | None) -> None:
    await bot.send_message(
        chat_id=os.environ.get("ADMIN_CHAT_ID"),
        text=text,
        parse_mode=parse_mode,
    )
