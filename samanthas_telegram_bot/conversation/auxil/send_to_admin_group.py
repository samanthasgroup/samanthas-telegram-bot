import os

from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode

load_dotenv()


async def send_to_admin_group(bot: Bot, text: str, parse_mode: ParseMode | None) -> None:
    await bot.send_message(
        chat_id=os.environ.get("ADMIN_CHAT_ID"),
        text=text,
        parse_mode=parse_mode,
    )
