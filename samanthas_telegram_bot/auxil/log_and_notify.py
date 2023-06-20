import logging
import os

from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.enums import LoggingLevel
from samanthas_telegram_bot.data_structures.constants import CALLER_LOGGING_STACK_LEVEL

load_dotenv()

logger = logging.getLogger(__name__)


async def log_and_notify(
    bot: Bot,
    level: LoggingLevel,
    text: str,
    stacklevel: int = CALLER_LOGGING_STACK_LEVEL,
    needs_to_notify_admin_group: bool = True,
    parse_mode_for_admin_group_message: ParseMode | None = None,
) -> None:
    """Sends message to logger, notifies admins if necessary.

    By default, shows calling function's name (due to default stack level).
    """
    getattr(logger, level)(text, stacklevel=stacklevel)
    if needs_to_notify_admin_group:
        await bot.send_message(
            chat_id=os.environ.get("ADMIN_CHAT_ID"),
            text=text,
            parse_mode=parse_mode_for_admin_group_message,
        )
