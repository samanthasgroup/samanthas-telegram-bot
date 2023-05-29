"""Functions for checking existence of entities with the backend."""
import logging

import httpx

from samanthas_telegram_bot.api_queries.auxil.constants import API_URL_PREFIX

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
