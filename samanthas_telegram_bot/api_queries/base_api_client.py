import logging

import httpx
from httpx import Response
from telegram import Update

from samanthas_telegram_bot.api_queries.auxil.constants import DataDict
from samanthas_telegram_bot.api_queries.auxil.enums import HttpMethod
from samanthas_telegram_bot.api_queries.auxil.exceptions import BaseApiClientError
from samanthas_telegram_bot.api_queries.auxil.models import NotificationParamsForStatusCode
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.data_structures.constants import CALLER_LOGGING_STACK_LEVEL
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES

logger = logging.getLogger(__name__)


class BaseApiClient:
    @classmethod
    async def get(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        url: str,
        notification_params_for_status_code: NotificationParamsForStatusCode,
        data: DataDict | None = None,
        params: DataDict | None = None,
    ) -> tuple[int, DataDict | None]:
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
            data=data,
            params=params,
            notification_params_for_status_code=notification_params_for_status_code,
        )

    @classmethod
    async def post(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        url: str,
        notification_params_for_status_code: NotificationParamsForStatusCode,
        data: DataDict,  # cannot be None for POST
        params: DataDict | None = None,
    ) -> tuple[int, DataDict | None]:
        """Makes a POST request, returns a tuple containing status code and JSON data.

        Note:
            Only pass **informative** status codes in ``notification_params_for_status_code``.
            E.g. If ``404 NOT FOUND`` means something relevant, pass it in, along with
            notification parameters (how to log and notify admins). For all other cases,
            let the API client raise its own exception and handle it accordingly
            (e.g. with an exception handler in the bot).
        """
        return await cls._make_request_and_get_data(
            method=HttpMethod.POST,
            update=update,
            context=context,
            url=url,
            data=data,
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
        data: DataDict | None = None,
        params: DataDict | None = None,
    ) -> tuple[int, DataDict | None]:
        response = await cls._make_async_request(method=method, url=url, data=data, params=params)
        status_code, json_data = cls._get_status_code_and_json(response)

        try:
            notification_params = notification_params_for_status_code[status_code]
        except KeyError as err:
            raise BaseApiClientError(
                f"Unexpected {status_code=} after sending a {method} "
                f"request to {url} with {data=}. JSON data received: {json_data}"
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

        return status_code, json_data

    @staticmethod
    async def _make_async_request(
        method: HttpMethod, url: str, data: DataDict | None = None, params: DataDict | None = None
    ) -> Response:
        async with httpx.AsyncClient() as client:
            if method == HttpMethod.GET:
                response = await client.get(url, params=params)
            elif method == HttpMethod.POST:
                response = await client.post(url, params=params, data=data)
            else:
                raise NotImplementedError(f"{method=} not supported")

        logger.debug(
            f"Sent {method.upper()} request to {url=} with {data=}. {response.status_code=}."
        )
        return response

    @staticmethod
    def _get_status_code_and_json(response: Response) -> tuple[int, DataDict]:
        status_code = response.status_code
        try:
            response_json = response.json()
        except AttributeError:
            raise BaseApiClientError(
                f"Response contains no JSON. Response status code: {status_code}"
            )

        logger.debug(f"JSON: {response_json}")
        return response.status_code, response_json
