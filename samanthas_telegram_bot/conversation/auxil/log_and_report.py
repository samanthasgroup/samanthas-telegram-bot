from logging import Logger
from typing import Literal

from telegram import Bot
from telegram.constants import ParseMode

from samanthas_telegram_bot.conversation.auxil.send_to_admin_group import send_to_admin_group


async def log_and_report(
    bot: Bot,
    logger: Logger,
    level: Literal["info", "error", "warning"],
    text: str,
    parse_mode: ParseMode | None,
) -> None:
    getattr(logger, level)(text)
    await send_to_admin_group(bot=bot, text=text, parse_mode=parse_mode)
