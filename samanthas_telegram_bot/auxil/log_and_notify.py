import logging
import os

from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.enums import LoggingLevel

load_dotenv()
logger = logging.getLogger(__name__)


async def log_and_notify(
    bot: Bot,
    level: LoggingLevel,
    text: str,
    needs_to_notify_admin_group: bool = True,
    parse_mode_for_admin_group_message: ParseMode | None = None,
) -> None:
    getattr(logger, level)(text)
    if needs_to_notify_admin_group:
        await bot.send_message(
            chat_id=os.environ.get("ADMIN_CHAT_ID"),
            text=text,
            parse_mode=parse_mode_for_admin_group_message,
        )
