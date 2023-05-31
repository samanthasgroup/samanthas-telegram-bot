import json
import os
from logging import Logger
from typing import Any

import httpx
from httpx import Response
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.constants import API_URL_PREFIX, DataDict
from samanthas_telegram_bot.api_queries.auxil.enums import (
    HttpMethod,
    LoggingLevel,
    SendToAdminGroupMode,
)
from samanthas_telegram_bot.auxil.escape_for_markdown import escape_for_markdown
from samanthas_telegram_bot.auxil.log_and_notify import log_and_notify
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES


def get_json(
    url_infix: str,
    logger: Logger,
    name_for_logger: str | None = None,
    params: dict[str, str] | None = None,
) -> Any:
    """Function for simple synchronous GET requests with logging."""
    if not name_for_logger:
        name_for_logger = url_infix.replace("_", " ")

    logger.info(f"Getting {name_for_logger} from the backend...")

    # synchronous requests are only run at application startup, so no exception handling needed
    response = httpx.get(f"{API_URL_PREFIX}/{url_infix}/", params=params)

    data = json.loads(response.content)
    logger.info(f"...received {len(data)} {name_for_logger}.")

    return data


async def send_to_backend(
    context: CUSTOM_CONTEXT_TYPES,  # type: ignore[valid-type]
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
    """Sends a request to backend, returns data, logs and notifies admins of potential errors.

    Returns data received from backend in response.

    This method is supposed to be called from within a chat (e.g. from a callback that has
    a context object passed to it).
    """
    response = await make_request(method=method, url=url, data=data)

    message_prefix = f"Chat {context.user_data.chat_id}: "  # type: ignore[attr-defined]
    message_suffix = ""
    failure_message_suffix = (
        f"{message_suffix} {response.status_code=} {response.content=} "
        f"@{os.environ.get('BOT_OWNER_USERNAME')}"
    )

    if parse_mode_for_admin_group_message == ParseMode.MARKDOWN_V2:
        message_prefix = escape_for_markdown(message_prefix)
        message_suffix = escape_for_markdown(message_suffix)
        failure_message_suffix = escape_for_markdown(failure_message_suffix)

    if response.status_code == expected_status_code:
        await log_and_notify(
            bot=context.bot,  # type: ignore[attr-defined]
            logger=logger,
            level=success_logging_level,
            text=f"{message_prefix}{success_message}{message_suffix}",
            needs_to_notify_admin_group=notify_admins_mode
            in (SendToAdminGroupMode.SUCCESS_ONLY, SendToAdminGroupMode.SUCCESS_AND_FAILURE),
            parse_mode_for_admin_group_message=parse_mode_for_admin_group_message,
        )
        logger.debug(f"{json.loads(response.content)=}")
        return json.loads(response.content)

    await log_and_notify(
        bot=context.bot,  # type: ignore[attr-defined]
        logger=logger,
        level=failure_logging_level,
        text=f"{message_prefix}{failure_message}{failure_message_suffix}",
        needs_to_notify_admin_group=notify_admins_mode
        in (SendToAdminGroupMode.FAILURE_ONLY, SendToAdminGroupMode.SUCCESS_AND_FAILURE),
        parse_mode_for_admin_group_message=parse_mode_for_admin_group_message,
    )
    return None


async def make_request(
    method: HttpMethod, url: str, data: DataDict | None = None, params: DataDict | None = None
) -> Response:
    async with httpx.AsyncClient() as client:
        if method == HttpMethod.GET:
            return await client.get(url, params=params)
        elif method == HttpMethod.POST:
            return await client.post(url, params=params, data=data)
        else:
            raise NotImplementedError(f"{method=} not supported")
