import csv
import json
import logging
from pathlib import Path

import httpx

PREFIX = "https://admin.samanthasgroup.com/api"
# TODO check for something different in case host is unavailable? Add decorators to all functions?
#  httpx.ConnectTimeout
logger = logging.getLogger(__name__)


async def chat_id_is_registered(chat_id: int) -> bool:
    """Checks whether the chat ID is already stored in the database."""
    logger.info(f"Checking with the backend if chat ID {chat_id} exists...")

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{PREFIX}/personal_info/check_existence_of_chat_id/",
            params={"registration_telegram_bot_chat_id": chat_id},
        )
    logger.debug(f"Response from backend after check for existence of {chat_id=}: {r.status_code}")
    if r.status_code == 200:
        logger.info(f"... {chat_id} already exists")
        return True
    logger.info(f"... {chat_id} doesn't exist")
    return False


async def get_age_ranges() -> dict[str, list[dict[str, str | int]]]:
    """Gets age ranges, assigns IDs (for bot phrases) to age ranges for teacher.

    The bot asks the teacher about students' ages, adding words like "teenager" or "adult"
    to the number ranges (e.g. "children (5-11)", in user's language).
    These words have to be assigned to these age ranges for the bot to display the correct phrase.
    For example: `phrases.csv` contains the phrase with ID ``option_adults``, so the age range
    corresponding to adults has to be assigned ``bot_phrase_id: option_adults``.
    """
    logger.info("Getting age ranges from the backend...")

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PREFIX}/age_ranges/")
    if r.status_code != 200:
        logger.error("Could not load age ranges")  # TODO alert the user

    data = json.loads(r.content)
    logger.info("... age ranges loaded successfully.")

    # prepare age ranges like {"student": [{"age_from": 5, "age_to": 7}, {...}, ...]}
    age_ranges = {
        type_: [item for item in data if item["type"] == type_] for type_ in ("student", "teacher")
    }

    # add IDs of bot phrases to teachers' age ranges
    age_to_phrase_id = {
        5: "young_children",
        9: "older_children",
        13: "adolescents",
        18: "adults",
        66: "seniors",
    }
    for age_range in age_ranges["teacher"]:
        age_range["bot_phrase_id"] = f"option_{age_to_phrase_id[age_range['age_from']]}"

    return age_ranges


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
