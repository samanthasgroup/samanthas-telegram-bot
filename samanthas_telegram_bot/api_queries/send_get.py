"""Functions for sending data to backend to create entities and get required data in return."""
import json
import logging

import httpx
from telegram import Bot, Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.conversation.auxil.log_and_report import log_and_report
from samanthas_telegram_bot.conversation.auxil.send_to_admin_group import send_to_admin_group
from samanthas_telegram_bot.data_structures.constants import API_URL_PREFIX
from samanthas_telegram_bot.data_structures.context_types import ChatData, UserData

logger = logging.getLogger(__name__)

STATUS_AT_CREATION_STUDENT_TEACHER = "awaiting_offer"
STATUS_AT_CREATION_TEACHER_UNDER_18 = "active"


async def _send_personal_info_get_id(user_data: UserData, bot: Bot) -> int:
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
        logger.info(
            f"Chat {user_data.chat_id}: Created personal data record for {user_data.first_name} "
            f"{user_data.last_name} ({user_data.email}), ID {data['id']}"
        )
        return data["id"]

    await log_and_report(
        text=(
            f"Chat {user_data.chat_id}: Failed to create personal data record "
            f"(code {r.status_code}, {r.content})"
        ),
        bot=bot,
        parse_mode=None,
        logger=logger,
        level="error",
    )
    return 0


async def send_student_info(update: Update, user_data: UserData) -> bool:
    """Sends a POST request to create a student and send results of assessment if any."""

    personal_info_id = await _send_personal_info_get_id(user_data=user_data, bot=update.get_bot())

    data = {
        "personal_info": personal_info_id,
        "comment": user_data.comment,
        "status": STATUS_AT_CREATION_STUDENT_TEACHER,
        "status_since": _format_status_since(update),
        "can_read_in_english": user_data.student_can_read_in_english,
        "is_member_of_speaking_club": False,  # TODO can backend set to False by default?
        "age_range": user_data.student_age_range_id,
        "availability_slots": user_data.day_and_time_slot_ids,
        "non_teaching_help_required": user_data.non_teaching_help_types,
        "teaching_languages_and_levels": user_data.language_and_level_ids,
    }

    if user_data.student_smalltalk_result:
        data["smalltalk_test_result"] = json.dumps(
            str(user_data.student_smalltalk_result.original_json)
        )
        # TODO url (when field in backend is created)

    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_URL_PREFIX}/students/", data=data)

    if r.status_code != httpx.codes.CREATED:
        await log_and_report(
            text=(
                f"Chat {user_data.chat_id}: Failed to create student ({r.status_code=}, "
                f"{r.content=})"
            ),
            logger=logger,
            level="error",
            bot=update.get_bot(),
            parse_mode=None,
        )
        return False

    logger.info(f"Chat {user_data.chat_id}: Created student ({personal_info_id=})")
    await send_to_admin_group(
        bot=update.get_bot(),
        text=(
            f"New student: [{user_data.first_name} {user_data.last_name}]"
            f"({API_URL_PREFIX}/student/{personal_info_id})"
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    if not user_data.student_assessment_answers:
        logger.info(f"Chat {user_data.chat_id}: no assessment answers to send")
        return True

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL_PREFIX}/enrollment_test_result/",
            data={
                "student": personal_info_id,
                "answers": [item.answer_id for item in user_data.student_assessment_answers],
            },
        )
    if r.status_code != httpx.codes.CREATED:
        await log_and_report(
            text=(
                f"Chat {user_data.chat_id}: Failed to send assessment "
                f"({r.status_code=}, {r.content=})"
            ),
            logger=logger,
            level="error",
            bot=update.get_bot(),
            parse_mode=None,
        )
        return False

    logger.info(f"Chat {user_data.chat_id}: Added assessment answers for {personal_info_id=}")
    return True


async def send_teacher_info(update: Update, user_data: UserData) -> bool:
    """Sends a POST request to create an adult teacher."""

    personal_info_id = await _send_personal_info_get_id(user_data=user_data, bot=update.get_bot())
    peer_help = user_data.teacher_peer_help

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL_PREFIX}/teachers/",
            data={
                "personal_info": personal_info_id,
                "comment": user_data.comment,
                "status": STATUS_AT_CREATION_STUDENT_TEACHER,
                "status_since": _format_status_since(update),
                "can_host_speaking_club": user_data.teacher_can_host_speaking_club,
                "has_hosted_speaking_club": False,
                "is_validated": False,
                "has_prior_teaching_experience": user_data.teacher_has_prior_experience,
                "non_teaching_help_provided_comment": user_data.teacher_additional_skills_comment,
                "peer_support_can_check_syllabus": peer_help.can_check_syllabus,
                "peer_support_can_host_mentoring_sessions": peer_help.can_host_mentoring_sessions,
                "peer_support_can_give_feedback": peer_help.can_give_feedback,
                "peer_support_can_help_with_childrens_groups": (
                    peer_help.can_help_with_children_group
                ),
                "peer_support_can_provide_materials": peer_help.can_provide_materials,
                "peer_support_can_invite_to_class": peer_help.can_invite_to_class,
                "peer_support_can_work_in_tandem": peer_help.can_work_in_tandem,
                "simultaneous_groups": user_data.teacher_number_of_groups,
                "weekly_frequency_per_group": user_data.teacher_class_frequency,
                "availability_slots": user_data.day_and_time_slot_ids,
                "non_teaching_help_provided": user_data.non_teaching_help_types,
                "student_age_ranges": user_data.teacher_student_age_range_ids,
                "teaching_languages_and_levels": user_data.language_and_level_ids,
            },
        )
    if r.status_code == httpx.codes.CREATED:
        await send_to_admin_group(
            bot=update.get_bot(),
            text=(
                f"New adult teacher: [{user_data.first_name} {user_data.last_name}]"
                f"({API_URL_PREFIX}/teacher/{personal_info_id})"
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        logger.info(f"Chat {user_data.chat_id}: Created adult teacher")
        return True

    await log_and_report(
        text=(
            f"Chat {user_data.chat_id}: Failed to create adult teacher "
            f"(code {r.status_code}, {r.content})"
        ),
        logger=logger,
        level="error",
        bot=update.get_bot(),
        parse_mode=None,
    )
    return False


async def send_teacher_under_18_info(update: Update, user_data: UserData) -> bool:
    """Sends a POST request to create a teacher under 18 years old."""

    personal_info_id = await _send_personal_info_get_id(user_data=user_data, bot=update.get_bot())

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL_PREFIX}/teachers_under_18/",
            data={
                "personal_info": personal_info_id,
                "comment": user_data.comment,
                "status_since": _format_status_since(update),
                "status": STATUS_AT_CREATION_TEACHER_UNDER_18,
                "can_host_speaking_club": user_data.teacher_can_host_speaking_club,
                "has_hosted_speaking_club": False,
                "is_validated": False,
                "non_teaching_help_provided_comment": user_data.teacher_additional_skills_comment,
                "teaching_languages_and_levels": user_data.language_and_level_ids,
            },
        )
    if r.status_code == httpx.codes.CREATED:
        await send_to_admin_group(
            bot=update.get_bot(),
            text=(
                f"New *young* teacher: [{user_data.first_name} {user_data.last_name}]"
                f"({API_URL_PREFIX}/teacherunder18/{personal_info_id})"
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        logger.info(f"Chat {user_data.chat_id}: Created young teacher")
        return True
    await log_and_report(
        text=(
            f"Chat {user_data.chat_id}: Failed to create young teacher "
            f"(code {r.status_code}, {r.content})"
        ),
        logger=logger,
        level="error",
        bot=update.get_bot(),
        parse_mode=None,
    )
    return False


def _format_status_since(update: Update) -> str:
    """Converts a datetime object into suitable format for `status_since` field."""
    # TODO can/should backend do this?
    return update.effective_message.date.isoformat().replace("+00:00", "Z")


async def send_written_answers_get_level(
    update: Update, chat_data: ChatData, user_data: UserData
) -> str | None:
    """Sends answers to written assessment to the backend, gets level and returns it."""
    answer_ids = tuple(
        item.answer_id for item in user_data.student_assessment_answers  # type: ignore[union-attr]
    )
    number_of_questions = len(chat_data.assessment.questions)  # type: ignore[union-attr]

    logger.info(
        f"Chat {user_data.chat_id}: Sending answers ({len(answer_ids)} out of "
        f"{number_of_questions} questions were answered) to backend and receiving level..."
    )

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL_PREFIX}/enrollment_test_result/get_level/",
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
    await log_and_report(
        text=(
            f"Chat {user_data.chat_id}: Failed to send results and receive level "
            f"(code {r.status_code}, {r.content})"
        ),
        logger=logger,
        level="error",
        bot=update.get_bot(),
        parse_mode=None,
    )
    return None
