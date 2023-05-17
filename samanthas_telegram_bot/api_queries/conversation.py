import json
import logging

import httpx
from telegram import Update

from samanthas_telegram_bot.data_structures.constants import API_URL_PREFIX
from samanthas_telegram_bot.data_structures.context_types import UserData

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
    if r.status_code == httpx.codes.OK:
        logger.info(f"... {chat_id} already exists")
        return True
    logger.info(f"... {chat_id} doesn't exist (response code {r.status_code})")
    return False


async def get_smalltalk_url(
    first_name: str,
    last_name: str,
    email: str,
) -> str:
    """Gets Smalltalk test URL from the back-end"""
    logger.info("Getting Smalltalk URL from backend...")
    return "(URL)"  # TODO


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
    if r.status_code == httpx.codes.OK:
        logger.info(f"... {data_to_check} does not exist")
        return False
    logger.info(f"... {data_to_check} already exists")
    return True


async def _send_personal_info_get_id(user_data: UserData) -> int:
    """Creates a personal info item. This function is meant to be called from other functions."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL_PREFIX}/personal_info/",
            data={
                "communication_language_mode": user_data.communication_language_in_class,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "telegram_username": user_data.tg_username if user_data.tg_username else "",
                "email": user_data.email,
                "phone": user_data.phone_number,
                "utc_timedelta": (
                    f"{user_data.utc_offset_hour:02d}:{user_data.utc_offset_minute}:00"
                ),
                "information_source": user_data.source,
                "registration_telegram_bot_chat_id": user_data.chat_id,
                "registration_telegram_bot_language": user_data.locale,
            },
        )
    if r.status_code == httpx.codes.CREATED:
        data = json.loads(r.content)
        logger.info(f"Chat {user_data.chat_id}: Created personal data record, ID {data['id']}")
        return data["id"]
    logger.error(f"Chat {user_data.chat_id}: Failed to create personal data record")
    return 0


async def send_student_info(update: Update, user_data: UserData) -> bool:
    """Sends a POST request to create a student."""

    personal_info_id = await _send_personal_info_get_id(user_data)

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL_PREFIX}/students/",
            data={
                "personal_info": personal_info_id,
                "comment": user_data.comment,
                "status_since": update.effective_message.date.isoformat().replace(
                    "+00:00", "Z"
                ),  # TODO can backend do this?
                "can_read_in_english": user_data.student_can_read_in_english,  # TODO what if None?
                "is_member_of_speaking_club": False,  # TODO can backend set to False by default?
                "smalltalk_test_result": {},  # TODO
                "age_range": user_data.student_age_range_id,
                "availability_slots": user_data.day_and_time_slot_ids,
                "non_teaching_help_required": user_data.non_teaching_help_types,
                "teaching_languages_and_levels": [],  # FIXME
            },
        )
    if r.status_code == httpx.codes.CREATED:
        logger.info(f"Chat {user_data.chat_id}: Created student")
        return True
    logger.error(
        f"Chat {user_data.chat_id}: Failed to create student (code {r.status_code}, {r.content})"
    )
    return False


async def send_written_answers_get_level(answers: dict[str, str]) -> str:
    """Sends answers to written assessment to the backend, gets level and returns it."""
    logger.info("Sending the results to the backend and receiving the level...")
    return "A2"  # TODO
