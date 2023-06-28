from dataclasses import dataclass

from telegram.constants import ParseMode

from samanthas_telegram_bot.api_clients.auxil.enums import LoggingLevel


@dataclass(frozen=True)
class NotificationParams:
    message: str
    logging_level: LoggingLevel = LoggingLevel.INFO
    notify_admins: bool = False
    parse_mode_for_bot_message: ParseMode | None = None


NotificationParamsForStatusCode = dict[int, NotificationParams]
