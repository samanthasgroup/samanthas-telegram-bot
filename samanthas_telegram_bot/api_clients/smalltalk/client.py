"""Functions for interaction with SmallTalk oral test service."""
import asyncio
import typing

import httpx
from telegram import Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_clients.auxil.constants import (
    MAX_ATTEMPTS_TO_GET_DATA_FROM_API,
    SMALLTALK_HEADERS,
    SMALLTALK_RESULTING_LEVEL_UNDEFINED,
    SMALLTALK_TEST_ID,
    SMALLTALK_TIMEOUT_IN_SECS_BETWEEN_API_REQUEST_ATTEMPTS,
    SMALLTALK_URL_GET_RESULTS,
    SMALLTALK_URL_GET_TEST,
    DataDict,
)
from samanthas_telegram_bot.api_clients.auxil.enums import SmalltalkTestStatus
from samanthas_telegram_bot.api_clients.auxil.models import NotificationParams
from samanthas_telegram_bot.api_clients.base.base_api_client import BaseApiClient
from samanthas_telegram_bot.api_clients.base.exceptions import BaseApiClientError
from samanthas_telegram_bot.api_clients.smalltalk.exceptions import (
    SmallTalkClientError,
    SmallTalkJSONParsingError,
    SmallTalkLogicError,
    SmallTalkRequestError,
)
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.data_structures.constants import ALL_LEVELS
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import LoggingLevel
from samanthas_telegram_bot.data_structures.models import SmalltalkResult


class SmallTalkClient(BaseApiClient):
    @classmethod
    async def send_user_data_get_test(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
    ) -> tuple[str | None, str | None]:
        """Gets SmallTalk interview ID and test URL."""
        user_data = context.user_data

        try:
            _, data = await cls.post(
                update=update,
                context=context,
                url=SMALLTALK_URL_GET_TEST,
                headers=SMALLTALK_HEADERS,
                json_data={
                    "test_id": SMALLTALK_TEST_ID,
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name,
                    "email": user_data.email,
                },  # TODO possibly webhook
                notification_params_for_status_code={
                    httpx.codes.OK: NotificationParams(
                        "Received data that should contain the link to SmallTalk test"
                    ),
                },
            )
        except BaseApiClientError as err:
            raise SmallTalkRequestError(
                "Failed to get data with test link from SmallTalk"
            ) from err

        # for mypy
        if not isinstance(data, dict):
            raise SmallTalkRequestError(f"Response from SmallTalk is not a dictionary: {data}")

        url = cls._get_value(data, "test_link")

        await logs(bot=context.bot, text=f"Received URL to oral test: {url}")

        return typing.cast(str, data["interview_id"]), typing.cast(str, url)

    @classmethod
    async def get_result(
        cls, update: Update, context: CUSTOM_CONTEXT_TYPES
    ) -> SmalltalkResult | None:
        """Gets results of SmallTalk interview."""

        user_data = context.user_data
        attempts = 0

        while True:
            await logs(
                bot=context.bot, update=update, text="Trying to receive results from SmallTalk"
            )

            try:
                result = await cls._process_data(
                    update=update,
                    context=context,
                    data=await cls._get_data(
                        update=update, context=context, test_id=user_data.student_smalltalk_test_id
                    ),
                )
            except SmallTalkClientError as err:
                user_data.comment = (
                    f"{user_data.comment}\n- Could not load results of SmallTalk assessment\n"
                    f"Interview ID: {user_data.student_smalltalk_test_id}"
                )
                raise SmallTalkClientError(
                    "Could not process SmallTalk results for "
                    f"{user_data.first_name} {user_data.last_name}"
                ) from err

            if result.status == SmalltalkTestStatus.NOT_STARTED_OR_IN_PROGRESS:
                await logs(
                    bot=context.bot,
                    update=update,
                    text=(
                        f"User {user_data.first_name} {user_data.last_name} "
                        f"didn't finish the SmallTalk assessment."
                    ),
                    needs_to_notify_admin_group=True,
                )
                user_data.comment = (
                    f"{user_data.comment}\n- SmallTalk assessment not finished\nCheck {result.url}"
                )
                return None
            elif result.status == SmalltalkTestStatus.RESULTS_NOT_READY:
                if attempts > MAX_ATTEMPTS_TO_GET_DATA_FROM_API:
                    total_seconds_waiting = (
                        MAX_ATTEMPTS_TO_GET_DATA_FROM_API
                        * SMALLTALK_TIMEOUT_IN_SECS_BETWEEN_API_REQUEST_ATTEMPTS
                    )
                    await logs(
                        bot=context.bot,
                        update=update,
                        level=LoggingLevel.ERROR,
                        text=(
                            f"SmallTalk results for {user_data.first_name} "
                            f"{user_data.last_name} still not ready after "
                            f"{total_seconds_waiting / 60} minutes. "
                            f"Interview ID {user_data.student_smalltalk_test_id}."
                        ),
                        needs_to_notify_admin_group=True,
                    )
                    user_data.comment = (
                        f"{user_data.comment}\n- SmallTalk assessment results were not ready\n"
                        f"Interview ID {user_data.student_smalltalk_test_id}"
                    )
                    return None

                await logs(
                    bot=context.bot, update=update, text="SmallTalk results not ready. Waiting..."
                )
                attempts += 1
                await asyncio.sleep(SMALLTALK_TIMEOUT_IN_SECS_BETWEEN_API_REQUEST_ATTEMPTS)
            else:
                await logs(
                    bot=context.bot,
                    update=update,
                    text=(
                        f'Received <a href="{result.url}">SmallTalk results for '
                        f"{user_data.first_name} {user_data.last_name}</a>"
                    ),
                    parse_mode_for_admin_group_message=ParseMode.HTML,
                    needs_to_notify_admin_group=True,
                )
                return result

    @classmethod
    async def _get_data(
        cls, update: Update, context: CUSTOM_CONTEXT_TYPES, test_id: str
    ) -> DataDict:
        user_data = context.user_data

        try:
            _, data = await cls.get(
                update=update,
                context=context,
                url=SMALLTALK_URL_GET_RESULTS,
                headers=SMALLTALK_HEADERS,
                params={
                    "id": test_id,
                    "additional_fields": (
                        "detailed_scores,strength_weaknesses,problem_statuses,problem_titles"
                    ),
                },
                notification_params_for_status_code={
                    httpx.codes.OK: NotificationParams(
                        # The data may not contain the results yet, we're just logging
                        # that status code was 200 OK and hence some data was received
                        f"Received data from SmallTalk after {user_data.first_name} "
                        f"{user_data.last_name}'s test"
                    )
                },
            )
        except BaseApiClientError as err:
            raise SmallTalkRequestError(
                "Failed to receive valid response from SmallTalk while getting test results."
            ) from err

        # for mypy
        if not isinstance(data, dict):
            raise SmallTalkRequestError(f"Response from SmallTalk is not a dictionary: {data}")

        return data

    @classmethod
    async def _process_data(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        data: DataDict,
    ) -> SmalltalkResult:
        status_name = cls._get_value(data, "status")
        try:
            status = SmalltalkTestStatus(status_name)
        except ValueError as err:
            raise SmallTalkLogicError(
                f"SmallTalk returned status '{status_name}' but we have no logic for it."
            ) from err

        if status == SmalltalkTestStatus.NOT_STARTED_OR_IN_PROGRESS:
            await logs(
                bot=context.bot, update=update, text="User has not yet completed the interview"
            )
        elif status == SmalltalkTestStatus.RESULTS_NOT_READY:
            await logs(
                bot=context.bot,
                update=update,
                text="User has completed the interview but the results are not ready",
            )

        if status != SmalltalkTestStatus.RESULTS_READY:
            return SmalltalkResult(status)

        level: str = cls._get_value(data, "score")
        level = level.strip()

        # 1. Strip off "p" in "B2p" and the like
        # 2. We use capital letters in our levels, so convert for easier comparison
        level_id = level.removesuffix("p").upper()

        if level.lower() == SMALLTALK_RESULTING_LEVEL_UNDEFINED:
            await logs(
                bot=context.bot,
                update=update,
                text="User did not pass enough oral tasks for level to be determined",
            )
            level_id = ""
        elif level_id not in ALL_LEVELS:
            raise SmallTalkJSONParsingError(f"Unrecognized language level returned: {level}")

        results_url = cls._get_value(data, "report_url")

        await logs(
            bot=context.bot,
            update=update,
            text=f"SmallTalk results: {status=}, {level=}, {results_url=}",
        )

        return SmalltalkResult(
            status=status,
            level=level_id,
            url=results_url,
            json=data,
        )

    @classmethod
    def _get_value(cls, data: DataDict, key: str) -> typing.Any:
        try:
            return super()._get_value(data, key)
        except BaseApiClientError as err:
            raise SmallTalkJSONParsingError(f"Could not parse SmallTalk {data=}") from err
