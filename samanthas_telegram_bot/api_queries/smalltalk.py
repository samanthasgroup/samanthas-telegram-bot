"""Functions for interaction with SmallTalk oral test service."""
import asyncio
import json
import logging
import os

import httpx
from telegram import Update

from samanthas_telegram_bot.data_structures.constants import ALL_LEVELS
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import SmalltalkTestStatus
from samanthas_telegram_bot.data_structures.helper_classes import SmalltalkResult

logger = logging.getLogger(__name__)

URL_PREFIX = "https://app.smalltalk2.me/api/integration"

HEADERS = {"Authorization": f"Bearer {os.environ.get('SMALLTALK_TOKEN')}"}
TEST_ID = os.environ.get("SMALLTALK_TEST_ID")


async def send_user_data_get_smalltalk_test(
    first_name: str,
    last_name: str,
    email: str,
) -> tuple[str | None, str | None]:
    """Gets Smalltalk interview ID and test URL."""

    async with httpx.AsyncClient() as client:
        r = await client.post(
            url=f"{URL_PREFIX}/send_test",
            headers=HEADERS,
            json={
                "test_id": TEST_ID,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },  # TODO possibly webhook
        )

    logger.debug(f"Request headers: {r.request.headers}, request content: {r.request.content}")
    data = json.loads(r.content)
    logger.debug(f"Response: {r.status_code=}, {r.headers=}, {r.content=}, {data=}")

    url = data.get("test_link", None)
    if url is None:
        logger.error("No oral test URL received")
        return None, None

    logger.info(f"Received URL to oral test: {url}")

    return data["interview_id"], url


async def get_smalltalk_result(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> SmalltalkResult | None:
    """Gets results of Smalltalk interview."""

    user_data = context.user_data

    while True:
        logger.info(f"Chat {user_data.chat_id}: Trying to receive results from Smalltalk")
        data = await get_json_with_results(user_data.student_smalltalk_test_id)
        result = process_smalltalk_json(data)
        attempts = 0

        if result is None:
            logger.error(f"Chat {user_data.chat_id}: Failed to receive data from Smalltalk")
            user_data.comment = (
                f"{user_data.comment}\n- Could not load results of Smalltalk assessment\n"
                f"Interview ID: {user_data.student_smalltalk_test_id}"
            )
            return None

        if result.status == SmalltalkTestStatus.NOT_STARTED_OR_IN_PROGRESS:
            logger.info(f"Chat {user_data.chat_id}: User didn't finish the assessment.")
            user_data.comment = (
                f"{user_data.comment}\n- Smalltalk assessment not finished\nCheck {result.url}"
            )
            return None
        elif result.status == SmalltalkTestStatus.RESULTS_NOT_READY:
            if attempts > 10:
                logger.error(
                    f"Chat {user_data.chat_id}: Smalltalk results still not ready after 5 minutes"
                )
                user_data.comment = (
                    f"{user_data.comment}\n- Smalltalk assessment results were not ready\n"
                    f"Check {result.url}"
                )

            logger.info(f"Chat {user_data.chat_id}: Smalltalk results not ready. Waiting...")
            attempts += 1
            await asyncio.sleep(30)
        else:
            return result


async def get_json_with_results(test_id: str) -> bytes:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url=f"{URL_PREFIX}/test_status",
            headers=HEADERS,
            params={
                "id": test_id,
                "additional_fields": (
                    "detailed_scores,strength_weaknesses,problem_statuses,problem_titles"
                ),
            },
        )

    logger.info(
        f"Request headers: {r.request.headers}. "
        f"Response: {r.status_code=}, {r.headers=}, {r.content=}"
    )
    return r.content


def process_smalltalk_json(json_data: bytes) -> SmalltalkResult | None:
    def level_is_undefined(str_: str) -> bool:
        return str_.lower().strip() == "undefined"

    try:
        loaded_data = json.loads(json_data)
    except json.decoder.JSONDecodeError:
        logger.error(f"Could not load JSON from {json_data=}")
        return None

    status = loaded_data["status"]

    # TODO Don't want to raise NotImplementedError here, but think about it
    if status not in SmalltalkTestStatus._value2member_map_:  # noqa
        logger.warning(f"Smalltalk returned {status=} but we have no logic for it.")

    if status == SmalltalkTestStatus.NOT_STARTED_OR_IN_PROGRESS:
        logger.info("User has not yet completed the interview")

    if status == SmalltalkTestStatus.RESULTS_NOT_READY:
        logger.info("User has completed the interview but the results are not ready")

    if status != SmalltalkTestStatus.RESULTS_READY:
        return SmalltalkResult(status=status)

    level = loaded_data["score"]
    level_id = level[:2]  # strip off "p" in "B2p" and the like

    if level_is_undefined(level):
        logger.info("User did not pass enough oral tasks for level to be determined")
        level_id = None

    if not (level_id in ALL_LEVELS or level_is_undefined(level)):
        logger.error(f"Unrecognized language level returned by SmallTalk: {level}")

    results_url = loaded_data["report_url"]

    logger.info(f"SmallTalk results: {status=}, {level=}, {results_url=}")

    return SmalltalkResult(
        status=status,
        level=level_id,
        url=results_url,
        original_json=json_data,
    )
