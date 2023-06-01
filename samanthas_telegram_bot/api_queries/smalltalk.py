"""Functions for interaction with SmallTalk oral test service."""
import asyncio
import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.constants import (
    SMALLTALK_MAX_ATTEMPTS_TO_GET_RESULTS,
    SMALLTALK_TIMEOUT_IN_SECS_BETWEEN_ATTEMPTS,
    SMALLTALK_URL_GET_RESULTS,
    SMALLTALK_URL_GET_TEST,
)
from samanthas_telegram_bot.api_queries.auxil.enums import LoggingLevel
from samanthas_telegram_bot.api_queries.auxil.exceptions import ApiRequestError
from samanthas_telegram_bot.auxil.log_and_notify import log_and_notify
from samanthas_telegram_bot.data_structures.constants import ALL_LEVELS
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import SmalltalkTestStatus
from samanthas_telegram_bot.data_structures.models import SmalltalkResult

load_dotenv()
logger = logging.getLogger(__name__)

HEADERS = {"Authorization": f"Bearer {os.environ.get('SMALLTALK_TOKEN')}"}
ORAL_TEST_ID = os.environ.get("SMALLTALK_TEST_ID")


async def send_user_data_get_smalltalk_test(
    first_name: str,
    last_name: str,
    email: str,
    context: CUSTOM_CONTEXT_TYPES,
) -> tuple[str | None, str | None]:
    """Gets SmallTalk interview ID and test URL."""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=SMALLTALK_URL_GET_TEST,
            headers=HEADERS,
            json={
                "test_id": ORAL_TEST_ID,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },  # TODO possibly webhook
        )

    data = response.json()
    try:
        url = data.get("test_link")
    except AttributeError:
        await log_and_notify(
            bot=context.bot,
            logger=logger,
            level=LoggingLevel.ERROR,
            text=f"SmallTalk returned invalid JSON when requested to send link to test: {data}",
        )
        return None, None

    if url is None:
        await log_and_notify(
            bot=context.bot,
            logger=logger,
            level=LoggingLevel.ERROR,
            text=f"SmallTalk returned JSON but it seems to contain no URL to test: {data}",
        )
        return None, None

    logger.info(f"Received URL to oral test: {url}")

    return data["interview_id"], url


async def get_smalltalk_result(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> SmalltalkResult | None:
    """Gets results of SmallTalk interview."""

    user_data = context.user_data

    while True:
        logger.info(f"Chat {user_data.chat_id}: Trying to receive results from SmallTalk")
        data = await get_json_with_results(
            test_id=user_data.student_smalltalk_test_id, context=context
        )
        if data is None:
            await log_and_notify(
                bot=context.bot,
                logger=logger,
                level=LoggingLevel.ERROR,
                # Error text in get_json_with_results() contains status code and response,
                # and here it contains user info:
                text=(
                    f"Chat {user_data.chat_id}: Failed to receive data from SmallTalk "
                    f"for {user_data.first_name} {user_data.last_name}"
                ),
            )
            return None

        result = process_smalltalk_json(data)
        attempts = 0

        if result is None:
            await log_and_notify(
                bot=context.bot,
                logger=logger,
                level=LoggingLevel.ERROR,
                text=(
                    f"Chat {user_data.chat_id}: Failed to process data from SmallTalk "
                    f"for {user_data.first_name} {user_data.last_name}"
                ),
            )
            user_data.comment = (
                f"{user_data.comment}\n- Could not load results of SmallTalk assessment\n"
                f"Interview ID: {user_data.student_smalltalk_test_id}"
            )
            return None

        if result.status == SmalltalkTestStatus.NOT_STARTED_OR_IN_PROGRESS:
            await log_and_notify(
                bot=context.bot,
                logger=logger,
                level=LoggingLevel.INFO,
                text=(
                    f"Chat {user_data.chat_id}: {user_data.first_name} {user_data.last_name} "
                    f"didn't finish the SmallTalk assessment."
                ),
            )
            user_data.comment = (
                f"{user_data.comment}\n- SmallTalk assessment not finished\nCheck {result.url}"
            )
            return None
        elif result.status == SmalltalkTestStatus.RESULTS_NOT_READY:
            if attempts > SMALLTALK_MAX_ATTEMPTS_TO_GET_RESULTS:
                total_seconds_waiting = (
                    SMALLTALK_MAX_ATTEMPTS_TO_GET_RESULTS
                    * SMALLTALK_TIMEOUT_IN_SECS_BETWEEN_ATTEMPTS
                )
                await log_and_notify(
                    bot=context.bot,
                    logger=logger,
                    level=LoggingLevel.ERROR,
                    text=(
                        f"Chat {user_data.chat_id}: SmallTalk results for {user_data.first_name} "
                        f"{user_data.last_name} still not ready after "
                        f"{total_seconds_waiting / 60} minutes. "
                        f"Interview ID {user_data.student_smalltalk_test_id}."
                    ),
                )
                user_data.comment = (
                    f"{user_data.comment}\n- SmallTalk assessment results were not ready\n"
                    f"Interview ID {user_data.student_smalltalk_test_id}"
                )

            logger.info(f"Chat {user_data.chat_id}: SmallTalk results not ready. Waiting...")
            attempts += 1
            await asyncio.sleep(SMALLTALK_TIMEOUT_IN_SECS_BETWEEN_ATTEMPTS)
        else:
            await log_and_notify(
                bot=context.bot,
                logger=logger,
                level=LoggingLevel.INFO,
                text=(
                    f"Chat {user_data.chat_id}: Received [SmallTalk results for "
                    f"{user_data.first_name} {user_data.last_name}]({result.url})"
                ),
                parse_mode_for_admin_group_message=ParseMode.MARKDOWN_V2,
            )
            return result


async def get_json_with_results(test_id: str, context: CUSTOM_CONTEXT_TYPES) -> Any:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url=SMALLTALK_URL_GET_RESULTS,
            headers=HEADERS,
            params={
                "id": test_id,
                "additional_fields": (
                    "detailed_scores,strength_weaknesses,problem_statuses,problem_titles"
                ),
            },
        )

    logger.debug(f"Request headers: {response.request.headers}.")
    if response.status_code == httpx.codes.OK:
        return response.json()

    await log_and_notify(
        bot=context.bot,
        logger=logger,
        level=LoggingLevel.ERROR,
        text=(
            f"Did not receive JSON from SmallTalk. {response.status_code=}, {response.headers=}, "
            f"{response.content=}"
        ),
    )

    return None


def process_smalltalk_json(data: Any) -> SmalltalkResult | None:
    try:
        status = data["status"]
    except KeyError:
        logger.error(f"No key 'status' found in JSON data. Keys: {', '.join(data.keys())}")
        return None

    if status not in SmalltalkTestStatus._value2member_map_:  # noqa
        raise ApiRequestError(f"SmallTalk returned {status=} but we have no logic for it.")

    if status == SmalltalkTestStatus.NOT_STARTED_OR_IN_PROGRESS:
        logger.info("User has not yet completed the interview")
    elif status == SmalltalkTestStatus.RESULTS_NOT_READY:
        logger.info("User has completed the interview but the results are not ready")

    if status != SmalltalkTestStatus.RESULTS_READY:
        return SmalltalkResult(status=status)

    level = data["score"]
    level_id = level[:2]  # strip off "p" in "B2p" and the like

    if level.lower().strip() == "undefined":
        logger.info("User did not pass enough oral tasks for level to be determined")
        level_id = None
    elif level_id not in ALL_LEVELS:
        logger.error(f"Unrecognized language level returned by SmallTalk: {level}")
        level_id = None

    results_url = data["report_url"]

    logger.info(f"SmallTalk results: {status=}, {level=}, {results_url=}")

    return SmalltalkResult(
        status=status,
        level=level_id,
        url=results_url,
        json=data,
    )
