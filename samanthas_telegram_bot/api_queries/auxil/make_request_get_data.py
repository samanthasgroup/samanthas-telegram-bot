import json
import os
from logging import Logger

import httpx
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.constants import DataDict
from samanthas_telegram_bot.api_queries.auxil.enums import (
    HttpMethod,
    LoggingLevel,
    SendToAdminGroupMode,
)
from samanthas_telegram_bot.auxil.escape_for_markdown import escape_for_markdown
from samanthas_telegram_bot.auxil.log_and_notify import log_and_notify
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES


async def make_request_get_data(
    context: CUSTOM_CONTEXT_TYPES,
    method: HttpMethod,
    url: str,
    data: DataDict,
    expected_status_code: int,
    logger: Logger,
    success_message: str,
    failure_message: str,
    success_logging_level: LoggingLevel = LoggingLevel.INFO,
    failure_logging_level: LoggingLevel = LoggingLevel.ERROR,
    notify_admins_mode: SendToAdminGroupMode = SendToAdminGroupMode.FAILURE_ONLY,
    parse_mode_for_admin_group_message: ParseMode | None = None,
) -> DataDict | None:
    """Sends a request, returns data, logs potential errors."""

    async with httpx.AsyncClient() as client:
        r = await getattr(client, method)(url, data=data)

    message_prefix = f"Chat {context.user_data.chat_id}: "
    message_suffix = f" status code {r.status_code}"
    failure_message_suffix = (
        f"{message_suffix} {r.content=} @{os.environ.get('BOT_OWNER_USERNAME')}"
    )

    if parse_mode_for_admin_group_message == ParseMode.MARKDOWN_V2:
        message_prefix = escape_for_markdown(message_prefix)
        message_suffix = escape_for_markdown(message_suffix)
        failure_message_suffix = escape_for_markdown(failure_message_suffix)

    if r.status_code == expected_status_code:
        await log_and_notify(
            text=f"{message_prefix}{success_message}{message_suffix}",
            logger=logger,
            level=success_logging_level,
            bot=context.bot,
            needs_to_notify_admin_group=notify_admins_mode
            in (SendToAdminGroupMode.SUCCESS_ONLY, SendToAdminGroupMode.SUCCESS_AND_FAILURE),
            parse_mode_for_admin_group_message=parse_mode_for_admin_group_message,
        )
        return json.loads(r.content)

    await log_and_notify(
        bot=context.bot,
        text=f"{message_prefix}{failure_message}{failure_message_suffix}",
        logger=logger,
        level=failure_logging_level,
        needs_to_notify_admin_group=notify_admins_mode
        in (SendToAdminGroupMode.FAILURE_ONLY, SendToAdminGroupMode.SUCCESS_AND_FAILURE),
        parse_mode_for_admin_group_message=parse_mode_for_admin_group_message,
    )
    return None
