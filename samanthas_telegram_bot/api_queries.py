import json
import logging

import httpx
from telegram import Update

from samanthas_telegram_bot.conversation.data_structures.age_range import AgeRange
from samanthas_telegram_bot.conversation.data_structures.assessment import (
    Assessment,
    AssessmentQuestion,
    AssessmentQuestionOption,
)
from samanthas_telegram_bot.conversation.data_structures.enums import AgeRangeType
from samanthas_telegram_bot.conversation.data_structures.user_data import UserData

logger = logging.getLogger(__name__)
PREFIX = "https://admin.samanthasgroup.com/api"
# TODO check for something different in case host is unavailable? Add decorators to all functions?
#  httpx.ConnectTimeout


async def chat_id_is_registered(chat_id: int) -> bool:
    """Checks whether the chat ID is already stored in the database."""
    logger.info(f"Checking with the backend if chat ID {chat_id} exists...")

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{PREFIX}/personal_info/check_existence_of_chat_id/",
            params={"registration_telegram_bot_chat_id": chat_id},
        )
    if r.status_code == httpx.codes.OK:
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
    if r.status_code == httpx.codes.OK:
        logger.info(f"... {data_to_check} does not exist")
        return False
    logger.info(f"... {data_to_check} already exists")
    return True


async def _send_personal_info_get_id(user_data: UserData) -> int:
    """Creates a personal info item. This function is meant to be called from other functions."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{PREFIX}/personal_info/",
            data={
                "communication_language_mode": user_data.communication_language_in_class,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "telegram_username": user_data.tg_username if user_data.tg_username else "",
                "email": user_data.email,
                "phone": user_data.phone_number,
                # TODO check:
                "utc_timedelta": f"{user_data.utc_offset_hour}:{user_data.utc_offset_minute}",
                "information_source": user_data.source,
                "registration_telegram_bot_chat_id": user_data.chat_id,
                "registration_telegram_bot_language": user_data.locale,
                "chatwoot_conversation_id": 0,  # TODO do not pass?
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
            f"{PREFIX}/students/",
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
                "availability_slots": [],  # FIXME
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


if __name__ == "__main__":
    get_assessments("en")
