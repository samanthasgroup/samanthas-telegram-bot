# TODO for now this module only contains dummy functions for the conversation flow to work.
import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def chat_id_is_registered(chat_id: int) -> bool:
    """Checks whether the chat ID is already stored in the database."""
    logger.info(f"Checking with the backend if chat ID {chat_id} exists...")
    return False


async def get_age_ranges() -> dict[str, list[dict[str, int]]]:
    logger.info("Getting age ranges from the backend...")
    return {
        "student": [
            {"age_from": 5, "age_to": 6},
            {"age_from": 7, "age_to": 8},
            {"age_from": 9, "age_to": 10},
            {"age_from": 11, "age_to": 12},
            {"age_from": 13, "age_to": 14},
            {"age_from": 15, "age_to": 17},
            {"age_from": 18, "age_to": 20},
            {"age_from": 21, "age_to": 25},
            {"age_from": 26, "age_to": 30},
            {"age_from": 31, "age_to": 35},
            {"age_from": 36, "age_to": 40},
            {"age_from": 41, "age_to": 45},
            {"age_from": 46, "age_to": 50},
            {"age_from": 51, "age_to": 55},
            {"age_from": 56, "age_to": 60},
            {"age_from": 61, "age_to": 65},
            {"age_from": 66, "age_to": 70},
            {"age_from": 71, "age_to": 75},
            {"age_from": 76, "age_to": 80},
            {"age_from": 81, "age_to": 85},
            {"age_from": 86, "age_to": 90},
            {"age_from": 91, "age_to": 95},
        ],
        "teacher": [],
        "matching": [],
    }


def get_assessment_questions(lang_code: str) -> tuple[dict[str, str], ...]:
    """Gets assessment questions, based on language and level"""

    # for some strange reason another ".parent" doesn't work, but ".." does
    DATA_DIR = Path(__name__).parent / ".." / "data"

    if lang_code != "en":
        # There is a difference between no test being available (that shouldn't raise an error)
        # and a wrong language code being passed
        raise ValueError(f"Wrong language code {lang_code}")

    path_to_test = DATA_DIR / "assessment_temp.csv"

    with path_to_test.open(encoding="utf-8", newline="") as fh:
        rows = tuple(csv.DictReader(fh))

    return rows


async def get_smalltalk_url(
    first_name: str,
    last_name: str,
    email: str,
) -> str:
    """Gets Smalltalk test URL from the back-end"""
    logger.info("Getting Smalltalk URL from backend...")
    return "(URL)"


async def person_with_first_name_last_name_email_exists_in_database(
    first_name: str,
    last_name: str,
    email: str,
) -> bool:
    """Checks whether user with given first and last name and email already exists in database."""
    logger.info(
        f"Checking with the backend if user {first_name} {last_name} ({email}) already exists..."
    )
    return False


async def send_written_answers_get_level(answers: dict[str, str]) -> str:
    """Sends answers to written assessment to the backend, gets level and returns it."""
    logger.info("Sending the results to the backend and receiving the level...")
    return "A2"
