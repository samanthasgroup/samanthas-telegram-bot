import json
import logging

import httpx

from samanthas_telegram_bot.conversation.data_structures.age_range import AgeRange
from samanthas_telegram_bot.conversation.data_structures.assessment import (
    Assessment,
    AssessmentQuestion,
    AssessmentQuestionOption,
)
from samanthas_telegram_bot.conversation.data_structures.enums import AgeRangeType

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
    if r.status_code == 200:
        logger.info(f"... {chat_id} already exists")
        return True
    logger.info(f"... {chat_id} doesn't exist (response code {r.status_code})")
    return False


def get_age_ranges() -> dict[AgeRangeType, tuple[AgeRange, ...]]:
    """Gets age ranges, assigns IDs (for bot phrases) to age ranges for teacher.

    The bot asks the teacher about students' ages, adding words like "teenager" or "adult"
    to the number ranges (e.g. "children (5-11)", in user's language).
    These words have to be assigned to these age ranges for the bot to display the correct phrase.
    For example: `phrases.csv` contains the phrase with ID ``option_adults``, so the age range
    corresponding to adults has to be assigned ``bot_phrase_id: option_adults``.

    Note: this is a **synchronous** function because it runs once before the application start.
    It being synchronous enables us to include it into ``BotData.__init__()``
    """
    logger.info("Getting age ranges from the backend...")

    # this operation is run at application startup, so no exception handling needed
    r = httpx.get(f"{PREFIX}/age_ranges/")

    data = json.loads(r.content)
    logger.info("... age ranges loaded successfully.")

    age_ranges: dict[AgeRangeType, tuple[AgeRange, ...]] = {
        type_: tuple(AgeRange(**item) for item in data if item["type"] == type_)
        for type_ in (AgeRangeType.STUDENT, AgeRangeType.TEACHER)
    }

    # add IDs of bot phrases to teachers' age ranges
    age_to_phrase_id = {
        5: "young_children",
        9: "older_children",
        13: "adolescents",
        18: "adults",
        66: "seniors",
    }
    for age_range in age_ranges[AgeRangeType.TEACHER]:
        age_range.bot_phrase_id = f"option_{age_to_phrase_id[age_range.age_from]}"

    return age_ranges


def get_assessments(lang_code: str) -> dict[int, Assessment]:
    """Gets assessment questions, based on language.

    Returns a dictionary matching an age range ID to assessment.

    Note: this is a **synchronous** function because it runs once before the application start.
    It being synchronous enables us to include it into ``BotData.__init__()``
    """

    logger.info(f"Getting assessment questions for {lang_code=}...")

    # this operation is run at application startup, so no exception handling needed
    r = httpx.get(f"{PREFIX}/enrollment_test/", params={"language": lang_code})

    data = json.loads(r.content)

    assessments = tuple(
        Assessment(
            id=item["id"],
            age_range_ids=tuple(item["age_ranges"]),
            questions=tuple(
                AssessmentQuestion(
                    id=question["id"],
                    text=question["text"],
                    options=tuple(
                        AssessmentQuestionOption(**option) for option in question["options"]
                    ),
                )
                for question in item["questions"]
            ),
        )
        for item in data
    )
    logger.info(f"... received {len(assessments)} assessments for {lang_code=}.")

    # Each assessment has a sequence of age range IDs. We have to match every single age range ID
    # in this sequence to a respective assessment.
    assessment_for_age_range_id = {
        age_range_id: assessment
        for assessment in assessments
        for age_range_id in assessment.age_range_ids
    }

    return assessment_for_age_range_id


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


if __name__ == "__main__":
    get_assessments("en")
