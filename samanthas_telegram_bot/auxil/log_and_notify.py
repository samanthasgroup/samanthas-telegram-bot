import logging
import os

from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.enums import LoggingLevel
from samanthas_telegram_bot.data_structures.constants import CALLER_LOGGING_STACK_LEVEL

load_dotenv()

logger = logging.getLogger(__name__)


async def logs(
    bot: Bot,
    level: LoggingLevel,
    text: str,
    stacklevel: int = CALLER_LOGGING_STACK_LEVEL,
    needs_to_notify_admin_group: bool = False,
    parse_mode_for_admin_group_message: ParseMode | None = None,
    update: Update | None = None,
) -> None:
    """Sends message to logger, notifies admins if necessary.

    If `Update` object is provided, displays chat ID and user info (as stored in Telegram).

    By default, shows calling function's name (due to default stack level).
    """
    full_text = (
        text
        if update is None
        else (
            f"Chat {update.effective_chat.id}, user {update.effective_user.full_name} "
            f"({update.effective_user.username}): {text}"
        )
    )

    getattr(logger, level)(full_text, stacklevel=stacklevel)

    if needs_to_notify_admin_group:
        await bot.send_message(
            chat_id=os.environ.get("ADMIN_CHAT_ID"),
            text=full_text,
            parse_mode=parse_mode_for_admin_group_message,
        )
