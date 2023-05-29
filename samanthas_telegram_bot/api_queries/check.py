"""Functions for checking existence of entities with the backend."""
import json
import logging

import httpx
from telegram import Update

from samanthas_telegram_bot.api_queries.auxil.constants import (
    API_URL_ENROLLMENT_TEST_GET_LEVEL,
    API_URL_PREFIX,
)
from samanthas_telegram_bot.api_queries.auxil.enums import LoggingLevel
from samanthas_telegram_bot.auxil.log_and_notify import log_and_notify
from samanthas_telegram_bot.data_structures.context_types import ChatData, UserData

logger = logging.getLogger(__name__)
# TODO check for something different in case host is unavailable? Add decorators to all functions?
#  httpx.ConnectTimeout


async def chat_id_is_registered(chat_id: int) -> bool:
    """Checks whether the chat ID is already stored in the database."""
    logger.info(f"Checking with the backend if chat ID {chat_id} exists...")

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{API_URL_PREFIX}/personal_info/check_existence_of_chat_id/",
            params={"registration_telegram_bot_chat_id": chat_id},
        )
    exists = r.status_code == httpx.codes.OK
    logger.info(f"... {chat_id} {exists=} ({r.status_code=})")
    return exists


async def person_with_first_name_last_name_email_exists_in_database(
    first_name: str,
    last_name: str,
    email: str,
) -> bool:
    """Checks whether user with given first and last name and email already exists in database."""
    data_to_check = f"user {first_name} {last_name} ({email})"

    logger.info(f"Checking with the backend if {data_to_check} already exists...")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL_PREFIX}/personal_info/check_existence/",
            data={"first_name": first_name, "last_name": last_name, "email": email},
        )

    # this is correct: `exists` is False if status is 200 OK
    exists = r.status_code != httpx.codes.OK
    logger.info(f"... {data_to_check} {exists=} ({r.status_code=})")
    return exists


async def get_level_of_written_test(
    update: Update, chat_data: ChatData, user_data: UserData
) -> str | None:
    """Sends answers to written assessment to the backend, gets level and returns it."""
    answer_ids = tuple(
        item.answer_id for item in user_data.student_assessment_answers  # type: ignore[union-attr]
    )
    number_of_questions = len(chat_data.assessment.questions)  # type: ignore[union-attr]

    logger.info(
        f"Chat {user_data.chat_id}: {len(answer_ids)} out of "
        f"{number_of_questions} questions were answered. Receiving level from backend..."
    )

    async with httpx.AsyncClient() as client:
        r = await client.post(
            API_URL_ENROLLMENT_TEST_GET_LEVEL,
            data={
                "answers": answer_ids,
                "number_of_questions": number_of_questions,
            },
        )
    if r.status_code == httpx.codes.OK:
        data = json.loads(r.content)
        level = data["resulting_level"]
        logger.info(f"Chat {user_data.chat_id}: Received level {level}.")
        return level
    await log_and_notify(
        bot=update.get_bot(),
        logger=logger,
        level=LoggingLevel.CRITICAL,
        text=(
            f"Chat {user_data.chat_id}: Failed to send results and receive level "
            f"(code {r.status_code}, {r.content})"
        ),
    )
    return None
