"""Functionality for sending data to backend to create people and get required data in return."""
import logging
import os
import typing

import httpx
from telegram import Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.constants import (
    API_URL_ENROLLMENT_TEST_SEND_RESULT,
    API_URL_PERSONAL_INFO_LIST_CREATE,
    API_URL_STUDENTS_LIST_CREATE,
    API_URL_TEACHER_RETRIEVE,
    API_URL_TEACHERS_LIST_CREATE,
    API_URL_YOUNG_TEACHERS_LIST_CREATE,
)
from samanthas_telegram_bot.api_queries.auxil.enums import (
    HttpMethod,
    LoggingLevel,
    SendToAdminGroupMode,
)
from samanthas_telegram_bot.api_queries.auxil.exceptions import ApiRequestError
from samanthas_telegram_bot.api_queries.auxil.requests_to_backend import send_to_backend
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import Role

logger = logging.getLogger(__name__)


# TODO how to best test these functions?  We can't test whether all data was collected by the bot,
#  but it may make sense to test whether all data is passed to backend (to avoid cases when we
#  add a new field to model and forget to reflect it here).  Is there some sort of "dry run" mode
#  in the backend so we can send a post request without the record being created?  Ofc, we can
#  just create a record and then delete it.


class PersonCreator:
    """Class for creating people (students, teachers...) in the backend."""

    @classmethod
    async def student(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> bool:
        """Sends a POST request to create a student and send results of assessment if any."""

        personal_info_id = await cls._personal_info_get_id(context)
        user_data = context.user_data

        result = await send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_STUDENTS_LIST_CREATE,
            data=user_data.student_as_dict(update=update, personal_info_id=personal_info_id),
            expected_status_code=httpx.codes.CREATED,
            logger=logger,
            success_message=cls._generate_success_message_for_person_creation(
                context=context, personal_info_id=personal_info_id
            ),
            failure_message=f"Failed to create student with ID {personal_info_id}",
            failure_logging_level=LoggingLevel.CRITICAL,
            notify_admins_mode=SendToAdminGroupMode.SUCCESS_AND_FAILURE,
            parse_mode_for_admin_group_message=ParseMode.MARKDOWN_V2,
        )

        if not user_data.student_assessment_answers:
            logger.info(f"Chat {user_data.chat_id}: no assessment answers to send")
            return result is not None

        result = await send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_ENROLLMENT_TEST_SEND_RESULT,
            data=user_data.student_enrollment_test_as_dict(personal_info_id=personal_info_id),
            expected_status_code=httpx.codes.CREATED,
            logger=logger,
            success_message=f"Added assessment answers for {personal_info_id=}",
            failure_message=f"Failed to send written assessment for {personal_info_id=})",
            failure_logging_level=LoggingLevel.CRITICAL,
            parse_mode_for_admin_group_message=ParseMode.MARKDOWN_V2,
        )
        return result is not None

    @classmethod
    async def teacher(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> bool:
        """Sends a POST request to create an adult teacher."""

        personal_info_id = await cls._personal_info_get_id(context)
        user_data = context.user_data

        result = await send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_TEACHERS_LIST_CREATE,
            data=user_data.teacher_as_dict(update=update, personal_info_id=personal_info_id),
            expected_status_code=httpx.codes.CREATED,
            logger=logger,
            success_message=cls._generate_success_message_for_person_creation(
                context=context, personal_info_id=personal_info_id
            ),
            failure_message=f"Failed to create adult teacher with ID {personal_info_id}",
            failure_logging_level=LoggingLevel.CRITICAL,
            notify_admins_mode=SendToAdminGroupMode.SUCCESS_AND_FAILURE,
            parse_mode_for_admin_group_message=ParseMode.MARKDOWN_V2,
        )
        return result is not None

    @classmethod
    async def teacher_under_18(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> bool:
        """Sends a POST request to create a teacher under 18 years old."""

        personal_info_id = await cls._personal_info_get_id(context)
        user_data = context.user_data

        result = await send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_YOUNG_TEACHERS_LIST_CREATE,
            data=user_data.teacher_under_18_as_dict(
                update=update, personal_info_id=personal_info_id
            ),
            expected_status_code=httpx.codes.CREATED,
            logger=logger,
            success_message=cls._generate_success_message_for_person_creation(
                context=context, personal_info_id=personal_info_id
            ),
            failure_message=f"Failed to create young teacher with ID {personal_info_id}",
            failure_logging_level=LoggingLevel.CRITICAL,
            notify_admins_mode=SendToAdminGroupMode.SUCCESS_AND_FAILURE,
            parse_mode_for_admin_group_message=ParseMode.MARKDOWN_V2,
        )
        return result is not None

    @staticmethod
    async def _personal_info_get_id(context: CUSTOM_CONTEXT_TYPES) -> int:
        """Creates a personal info item and returns its ID."""
        user_data = context.user_data
        common_message_part = (
            f"personal data record for {user_data.first_name} "
            f"{user_data.last_name} ({user_data.email})"
        )
        failure_message = f"Failed to create {common_message_part}"

        data = await send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_PERSONAL_INFO_LIST_CREATE,
            data=user_data.personal_info_as_dict(),
            expected_status_code=httpx.codes.CREATED,
            logger=logger,
            success_message=f"Created {common_message_part}",
            failure_message=failure_message,
            failure_logging_level=LoggingLevel.CRITICAL,
        )
        if data:
            logger.info(f"{data['id']=}")
            return typing.cast(int, data["id"])
        raise ApiRequestError(failure_message)

    @staticmethod
    def _generate_success_message_for_person_creation(
        context: CUSTOM_CONTEXT_TYPES, personal_info_id: int
    ) -> str:
        user_data = context.user_data

        teacher_age_infix = (
            "young " if user_data.role == Role.TEACHER and user_data.teacher_is_under_18 else ""
        )

        success_message = (
            f"Created {teacher_age_infix}{user_data.role} "
            f"[{user_data.first_name} {user_data.last_name}]"
            f"({API_URL_TEACHER_RETRIEVE}{personal_info_id}), ID {personal_info_id}\\."
        )
        if user_data.role == Role.TEACHER and user_data.teacher_can_host_speaking_club:
            success_message += (
                f" @{os.environ.get('SPEAKING_CLUB_COORDINATOR_USERNAME')} "
                "this teacher can host speaking clubs\\."
            )

        return success_message
