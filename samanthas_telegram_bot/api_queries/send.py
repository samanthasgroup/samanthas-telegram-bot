import json
import logging

import httpx
from telegram import Update

from samanthas_telegram_bot.data_structures.constants import API_URL_PREFIX
from samanthas_telegram_bot.data_structures.context_types import UserData

logger = logging.getLogger(__name__)


async def get_smalltalk_url(
    first_name: str,
    last_name: str,
    email: str,
) -> str:
    """Gets Smalltalk test URL from the back-end"""
    logger.info("Getting Smalltalk URL from backend...")
    return "(URL)"  # TODO


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
                "teaching_languages_and_levels": user_data.language_and_level_ids,
            },
            # TODO status
            # TODO send answers to assessment here (backend cannot store them earlier when
            #  determining student's level because student is not created yet at that point).
        )
    if r.status_code == httpx.codes.CREATED:
        logger.info(f"Chat {user_data.chat_id}: Created student")
        return True
    logger.error(
        f"Chat {user_data.chat_id}: Failed to create student (code {r.status_code}, {r.content})"
    )
    return False


async def send_teacher_info(update: Update, user_data: UserData) -> bool:  # TODO young teacher
    """Sends a POST request to create a teacher."""

    personal_info_id = await _send_personal_info_get_id(user_data)
    peer_help = user_data.teacher_peer_help

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_URL_PREFIX}/teachers/",
            data={
                "personal_info": personal_info_id,
                "comment": user_data.comment,
                "status_since": update.effective_message.date.isoformat().replace(
                    "+00:00", "Z"
                ),  # TODO can backend do this?
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
            # TODO status
        )
    if r.status_code == httpx.codes.CREATED:
        logger.info(f"Chat {user_data.chat_id}: Created teacher")
        return True
    logger.error(
        f"Chat {user_data.chat_id}: Failed to create teacher (code {r.status_code}, {r.content})"
    )
    return False


async def send_written_answers_get_level(answers: dict[str, str]) -> str:
    """Sends answers to written assessment to the backend, gets level and returns it."""
    logger.info("Sending the results to the backend and receiving the level...")
    return "A2"  # TODO
