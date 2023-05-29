"""Functions for checking info (e.g. existence of entities) with the backend."""
import logging
import typing

import httpx

from samanthas_telegram_bot.api_queries.auxil.constants import (
    API_URL_CHECK_EXISTENCE_OF_CHAT_ID,
    API_URL_CHECK_EXISTENCE_OF_PERSONAL_INFO,
    API_URL_ENROLLMENT_TEST_GET_LEVEL,
)
from samanthas_telegram_bot.api_queries.auxil.enums import (
    HttpMethod,
    LoggingLevel,
    SendToAdminGroupMode,
)
from samanthas_telegram_bot.api_queries.auxil.requests_to_backend import (
    make_request,
    send_to_backend,
)
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES

logger = logging.getLogger(__name__)
# TODO check for something different in case host is unavailable? Add decorators to all functions?
#  httpx.ConnectTimeout


async def chat_id_is_registered(chat_id: int) -> bool:
    """Checks whether the chat ID is already stored in the database."""
    logger.info(f"Checking with the backend if chat ID {chat_id} exists...")

    response = await make_request(
        method=HttpMethod.GET,
        url=API_URL_CHECK_EXISTENCE_OF_CHAT_ID,
        params={"registration_telegram_bot_chat_id": chat_id},
    )

    exists = response.status_code == httpx.codes.OK
    logger.info(f"... {chat_id} {exists=} ({response.status_code=})")
    return exists


async def person_with_first_name_last_name_email_exists_in_database(
    first_name: str,
    last_name: str,
    email: str,
) -> bool:
    """Checks whether user with given first and last name and email already exists in database."""
    data_to_check = f"user {first_name} {last_name} ({email})"

    logger.info(f"Checking with the backend if {data_to_check} already exists...")
    response = await make_request(
        method=HttpMethod.POST,
        url=API_URL_CHECK_EXISTENCE_OF_PERSONAL_INFO,
        data={"first_name": first_name, "last_name": last_name, "email": email},
    )

    # this is correct: `exists` is False if status is 200 OK
    exists = response.status_code != httpx.codes.OK
    logger.info(f"... {data_to_check} {exists=} ({response.status_code=})")
    return exists


async def get_level_of_written_test(
    context: CUSTOM_CONTEXT_TYPES,
) -> str | None:
    """Sends answers to written assessment to the backend, gets level and returns it."""
    user_data = context.user_data

    answer_ids: tuple[int, ...] = tuple(
        item.answer_id for item in user_data.student_assessment_answers
    )
    number_of_questions = len(context.chat_data.assessment.questions)

    logger.info(
        f"Chat {user_data.chat_id}: {len(answer_ids)} out of "
        f"{number_of_questions} questions were answered. Receiving level from backend..."
    )

    data = await send_to_backend(
        context=context,
        method=HttpMethod.POST,
        url=API_URL_ENROLLMENT_TEST_GET_LEVEL,
        data={"answers": answer_ids, "number_of_questions": number_of_questions},
        expected_status_code=httpx.codes.OK,
        logger=logger,
        success_message="Checked result of written assessment:",
        failure_message="Failed to send results of written assessment and receive level",
        failure_logging_level=LoggingLevel.CRITICAL,
        notify_admins_mode=SendToAdminGroupMode.FAILURE_ONLY,
    )

    try:
        level = typing.cast(str, data["level"])  # type: ignore[index]
    except KeyError:
        return None

    logger.info(f"{level=}")
    return level
