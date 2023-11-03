import logging

from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.auxil.constants import ADMIN_CHAT_ID, CALLER_LOGGING_STACK_LEVEL
from samanthas_telegram_bot.data_structures.enums import LoggingLevel

load_dotenv()

logger = logging.getLogger(__name__)


async def logs(
    bot: Bot,
    text: str,
    level: LoggingLevel = LoggingLevel.INFO,
    stacklevel: int = CALLER_LOGGING_STACK_LEVEL,
    needs_to_notify_admin_group: bool = False,
    parse_mode_for_admin_group_message: ParseMode | None = ParseMode.HTML,
    update: Update | None = None,
) -> None:
    """Sends message to logger, notifies admins if necessary.

    If `Update` object is provided, displays chat ID and user info (as stored in Telegram).

    By default, shows calling function's name (due to default stack level).
    """
    extra_info = ""

    if isinstance(update, Update):
        user = update.effective_user
        username_note = f" ({user.username})" if user.username else ""
        extra_info = f"Chat {update.effective_chat.id}, user {user.full_name}{username_note}: "

    full_text = f"{extra_info}{text}"

    getattr(logger, level)(full_text, stacklevel=stacklevel)

    if needs_to_notify_admin_group:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=full_text,
            parse_mode=parse_mode_for_admin_group_message,
        )
