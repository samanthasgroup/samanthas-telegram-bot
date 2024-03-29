import asyncio
import logging
from typing import Any

import httpx
from httpx import Response
from telegram import Update

from samanthas_telegram_bot.api_clients.auxil.constants import (
    BASE_TIMEOUT_IN_SECS_BETWEEN_API_REQUEST_ATTEMPTS,
    MAX_ATTEMPTS_TO_GET_DATA_FROM_API,
    DataDict,
)
from samanthas_telegram_bot.api_clients.auxil.enums import HttpMethod
from samanthas_telegram_bot.api_clients.auxil.models import NotificationParamsForStatusCode
from samanthas_telegram_bot.api_clients.base.exceptions import BaseApiClientError
from samanthas_telegram_bot.auxil.constants import CALLER_LOGGING_STACK_LEVEL
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import LoggingLevel

logger = logging.getLogger(__name__)


class BaseApiClient:
    """Base class for making API requests.

    Implements GET and POST methods that take update and context and provide extended
    functionality and require ``update`` and ``context``, as well as simple synchronous GET
    requests.
    """

    @classmethod
    async def get(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        url: str,
        notification_params_for_status_code: NotificationParamsForStatusCode,
        headers: dict[str, str] | None = None,
        params: DataDict | None = None,
    ) -> tuple[int, DataDict | list[DataDict]]:
        """Makes a GET request, returns a tuple containing status code and JSON data.

        Note:
            Only pass **informative** status codes in ``notification_params_for_status_code``.
            E.g. If ``404 NOT FOUND`` means something relevant, pass it in, along with
            notification parameters (how to log and notify admins). For all other cases,
            let the API client raise its own exception and handle it accordingly
            (e.g. with an exception handler in the bot).
        """
        return await cls._make_request_and_get_data(
            method=HttpMethod.GET,
            update=update,
            context=context,
            url=url,
            headers=headers,
            params=params,
            notification_params_for_status_code=notification_params_for_status_code,
        )

    @staticmethod
    def get_simple(
        url: str, headers: dict[str, str] | None = None, params: dict[str, str] | None = None
    ) -> DataDict | list[DataDict]:
        """A simple method for a synchronous GET request, not needing update or context."""
        response = httpx.get(url, headers=headers, params=params)
        return response.json()

    @classmethod
    async def post(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        url: str,
        notification_params_for_status_code: NotificationParamsForStatusCode,
        headers: dict[str, str] | None = None,
        data: DataDict | None = None,
        json_data: DataDict | None = None,
        params: DataDict | None = None,
    ) -> tuple[int, DataDict | list[DataDict]]:
        """Makes a POST request, returns a tuple containing status code and JSON data.

        The ``data`` parameter is passed as ``data``, ``json_data`` as ``json`` to
        httpx client. You can pass either one of them, but not both at the same time.

        Note:
            Only pass **informative** status codes in ``notification_params_for_status_code``.
            E.g. If ``404 NOT FOUND`` means something relevant, pass it in, along with
            notification parameters (how to log and notify admins). For all other cases,
            let the API client raise its own exception and handle it accordingly
            (e.g. with an exception handler in the bot).
        """
        await logs(
            bot=context.bot,
            update=update,
            level=LoggingLevel.DEBUG,
            text=f"Sending a POST request to {url} with {headers=}, {data=}, {json_data=}",
        )

        if data is None and json_data is None:
            raise TypeError("Either `data` or `json_data` must be provided. You passed nothing.")

        if data is not None and json_data is not None:
            raise TypeError("Either `data` or `json_data` must be provided, not both.")

        return await cls._make_request_and_get_data(
            method=HttpMethod.POST,
            update=update,
            context=context,
            url=url,
            headers=headers,
            data=data,
            json_data=json_data,
            params=params,
            notification_params_for_status_code=notification_params_for_status_code,
        )

    @classmethod
    async def _make_request_and_get_data(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        method: HttpMethod,
        url: str,
        notification_params_for_status_code: NotificationParamsForStatusCode,
        headers: dict[str, str] | None = None,
        data: DataDict | None = None,
        json_data: DataDict | None = None,
        params: DataDict | None = None,
    ) -> tuple[int, DataDict | list[DataDict]]:
        response = await cls._make_request_with_retries(
            update=update,
            context=context,
            method=method,
            url=url,
            headers=headers,
            data=data,
            json_data=json_data,
            params=params,
        )

        try:
            status_code, response_json_data = await cls._get_status_code_and_json(
                update=update, context=context, response=response
            )
        except AttributeError as err:
            raise BaseApiClientError("Could not load JSON") from err

        try:
            notification_params = notification_params_for_status_code[status_code]
        except KeyError as err:
            raise BaseApiClientError(
                f"Unexpected {status_code=} after sending a {method} "
                f"request to {url} with {data=}. JSON data received: {response_json_data}"
            ) from err

        await logs(
            bot=context.bot,
            level=notification_params.logging_level,
            text=notification_params.message,
            # API client creates one additional layer between caller and logger
            stacklevel=CALLER_LOGGING_STACK_LEVEL + 1,
            needs_to_notify_admin_group=notification_params.notify_admins,
            parse_mode_for_admin_group_message=notification_params.parse_mode_for_bot_message,
            update=update,
        )

        return status_code, response_json_data

    @classmethod
    async def _make_request_with_retries(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        method: HttpMethod,
        url: str,
        headers: dict[str, str] | None = None,
        data: DataDict | None = None,
        json_data: DataDict | None = None,
        params: DataDict | None = None,
    ) -> Response:
        attempts = 0
        timeout = BASE_TIMEOUT_IN_SECS_BETWEEN_API_REQUEST_ATTEMPTS

        while True:
            try:
                response = await cls._make_one_request(
                    update=update,
                    context=context,
                    method=method,
                    url=url,
                    headers=headers,
                    data=data,
                    json_data=json_data,
                    params=params,
                )
            except (NotImplementedError, httpx.TransportError) as err:
                # TODO logic can be split here, maybe let user try again in case of httpx error.
                raise BaseApiClientError(
                    f"Failed to send {method.upper()} request to {url=}"
                ) from err

            if response.status_code not in (
                httpx.codes.INTERNAL_SERVER_ERROR,
                httpx.codes.BAD_GATEWAY,
                httpx.codes.SERVICE_UNAVAILABLE,
                httpx.codes.GATEWAY_TIMEOUT,
            ):
                return response

            attempts += 1
            if attempts == MAX_ATTEMPTS_TO_GET_DATA_FROM_API:
                raise BaseApiClientError(f"Failed to reach {url} after {attempts} attempts.")

            await cls._log_retry(
                update=update,
                context=context,
                url=url,
                method=method,
                status_code=response.status_code,
                attempts=attempts,
                timeout=timeout,
            )

            await asyncio.sleep(timeout)
            timeout *= 2

    @staticmethod
    async def _make_one_request(
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        method: HttpMethod,
        url: str,
        headers: dict[str, str] | None = None,
        data: DataDict | None = None,
        json_data: DataDict | None = None,
        params: DataDict | None = None,
    ) -> Response:
        async with httpx.AsyncClient() as client:
            if method == HttpMethod.GET:
                response = await client.get(url, headers=headers, params=params)
            elif method == HttpMethod.POST:
                response = await client.post(
                    url, headers=headers, params=params, data=data, json=json_data
                )
            else:
                raise NotImplementedError(f"{method=} not supported")

        await logs(
            bot=context.bot,
            update=update,
            text=f"Sent {method.upper()} request to {url=} with {data=}. {response.status_code=}.",
            level=LoggingLevel.DEBUG,
        )
        return response

    @staticmethod
    async def _log_retry(
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        url: str,
        method: HttpMethod,
        status_code: int,
        timeout: int,
        attempts: int,
    ) -> None:
        if attempts == 1:
            await logs(
                bot=context.bot,
                update=update,
                text=(
                    f"Failed to reach {url=} with {method=} ({status_code=}). "
                    f"Will try {MAX_ATTEMPTS_TO_GET_DATA_FROM_API - attempts} times before failing"
                ),
                level=LoggingLevel.WARNING,
                needs_to_notify_admin_group=True,
            )
            return

        await logs(
            bot=context.bot,
            update=update,
            text=(
                f"Failed to reach {url=} with {method=} ({status_code=}). "
                f"Next attempt in {timeout} seconds "
                f"({MAX_ATTEMPTS_TO_GET_DATA_FROM_API - attempts} attempts left)."
            ),
            level=LoggingLevel.WARNING,
        )
        return

    @staticmethod
    async def _get_status_code_and_json(
        update: Update, context: CUSTOM_CONTEXT_TYPES, response: Response
    ) -> tuple[int, DataDict | list[DataDict]]:
        status_code = response.status_code
        await logs(
            bot=context.bot,
            update=update,
            level=LoggingLevel.DEBUG,
            text=f"Received response {status_code}, {response.content=}",
        )
        try:
            response_json: DataDict | list[DataDict] = response.json()
        except AttributeError as err:
            raise AttributeError(
                f"Response contains no JSON. Response status code: {status_code}"
            ) from err

        await logs(
            bot=context.bot, text=f"JSON: {response_json}", update=update, level=LoggingLevel.DEBUG
        )
        return response.status_code, response_json

    @staticmethod
    def _get_value(data: DataDict, key: str) -> Any:
        try:
            return data[key]
        except KeyError:
            raise BaseApiClientError(
                f"No key '{key}' found in JSON data. Keys: {', '.join(data.keys())}"
            )
