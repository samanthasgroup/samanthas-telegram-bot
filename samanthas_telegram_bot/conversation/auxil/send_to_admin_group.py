import os

from telegram import Bot
from telegram.constants import ParseMode


async def send_to_admin_group(bot: Bot, text: str, parse_mode: ParseMode | None) -> None:
    await bot.send_message(
        chat_id=os.environ.get("ADMIN_CHAT_ID"),
        text=text,
        parse_mode=parse_mode,
    )
