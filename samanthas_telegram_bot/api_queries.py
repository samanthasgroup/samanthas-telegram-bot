import csv
import json
import logging
from pathlib import Path

import httpx

PREFIX = "https://admin.samanthasgroup.com/api"
# TODO check for something different in case host is unavailable? Add decorators to all functions?

logger = logging.getLogger(__name__)


async def chat_id_is_registered(chat_id: int) -> bool:
    """Checks whether the chat ID is already stored in the database."""
    logger.info(f"Checking with the backend if chat ID {chat_id} exists...")
    return False  # TODO


async def get_age_ranges() -> dict[str, list[dict[str, int]]]:
    logger.info("Getting age ranges from the backend...")

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PREFIX}/age_ranges/")
    if r.status_code != 200:
        logger.error("Could not load age ranges")  # TODO alert the user

    data = json.loads(r.content)
    logger.info("... age ranges loaded successfully.")

    return {
        type_: [item for item in data if item["type"] == type_]
        for type_ in ("student", "teacher")
        # TODO teacher age ranges are not used yet
        # TODO store IDs of age ranges during conversation
    }


def get_assessment_questions(lang_code: str) -> tuple[dict[str, str], ...]:
    """Gets assessment questions, based on language and level"""

    DATA_DIR = Path(__name__).resolve().parent.parent / "data"

    if lang_code != "en":
        # There is a difference between no test being available (that shouldn't raise an error)
        # and a wrong language code being passed
        raise ValueError(f"Wrong language code {lang_code}")

    path_to_test = DATA_DIR / "assessment_temp.csv"

    with path_to_test.open(encoding="utf-8", newline="") as fh:
        rows = tuple(csv.DictReader(fh))

    return rows  # TODO


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
            f"{PREFIX}/personal_info/check_existence/",
            data={"first_name": first_name, "last_name": last_name, "email": email},
        )
    if r.status_code == 200:
        logger.info(f"... {data_to_check} does not exist")
        return False
    logger.info(f"... {data_to_check} already exists")
    return True


async def send_written_answers_get_level(answers: dict[str, str]) -> str:
    """Sends answers to written assessment to the backend, gets level and returns it."""
    logger.info("Sending the results to the backend and receiving the level...")
    return "A2"  # TODO
