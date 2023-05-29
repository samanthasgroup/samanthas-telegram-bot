"""Functionality for sending data to backend to create people and get required data in return."""
import logging
import typing

import httpx
from telegram import Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.constants import (
    API_URL_ENROLLMENT_TEST_SEND_RESULT,
    API_URL_PERSONAL_INFO_LIST_CREATE,
    API_URL_STUDENT_RETRIEVE,
    API_URL_STUDENTS_LIST_CREATE,
    API_URL_TEACHER_RETRIEVE,
    API_URL_TEACHERS_LIST_CREATE,
    API_URL_YOUNG_TEACHER_RETRIEVE,
    API_URL_YOUNG_TEACHERS_LIST_CREATE,
)
from samanthas_telegram_bot.api_queries.auxil.data_maker import DataMaker
from samanthas_telegram_bot.api_queries.auxil.enums import (
    HttpMethod,
    LoggingLevel,
    SendToAdminGroupMode,
)
from samanthas_telegram_bot.api_queries.auxil.make_request_get_data import make_request_get_data
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES

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

        result = await make_request_get_data(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_STUDENTS_LIST_CREATE,
            data=DataMaker.student(
                update=update, personal_info_id=personal_info_id, user_data=user_data
            ),
            expected_status_code=httpx.codes.CREATED,
            logger=logger,
            success_message=(
                f"Created student [{user_data.first_name} {user_data.last_name}]"
                f"({API_URL_STUDENT_RETRIEVE}{personal_info_id}), ID {personal_info_id}"
            ),
            failure_message=f"Failed to create student with ID {personal_info_id}",
            failure_logging_level=LoggingLevel.CRITICAL,
            notify_admins_mode=SendToAdminGroupMode.SUCCESS_AND_FAILURE,
            parse_mode_for_admin_group_message=ParseMode.MARKDOWN_V2,
        )

        if not user_data.student_assessment_answers:
            logger.info(f"Chat {user_data.chat_id}: no assessment answers to send")
            return result is not None

        result = await make_request_get_data(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_ENROLLMENT_TEST_SEND_RESULT,
            data=DataMaker.student_enrollment_test(
                personal_info_id=personal_info_id, user_data=user_data
            ),
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

        result = await make_request_get_data(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_TEACHERS_LIST_CREATE,
            data=DataMaker.teacher(
                update=update, personal_info_id=personal_info_id, user_data=user_data
            ),
            expected_status_code=httpx.codes.CREATED,
            logger=logger,
            success_message=(
                f"Created adult teacher [{user_data.first_name} {user_data.last_name}]"
                f"({API_URL_TEACHER_RETRIEVE}{personal_info_id}), ID {personal_info_id}"
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

        result = await make_request_get_data(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_YOUNG_TEACHERS_LIST_CREATE,
            data=DataMaker.teacher_under_18(
                update=update, personal_info_id=personal_info_id, user_data=user_data
            ),
            expected_status_code=httpx.codes.CREATED,
            logger=logger,
            success_message=(
                f"Created young teacher [{user_data.first_name} {user_data.last_name}]"
                f"({API_URL_YOUNG_TEACHER_RETRIEVE}{personal_info_id}), ID {personal_info_id}"
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

        data = await make_request_get_data(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_PERSONAL_INFO_LIST_CREATE,
            data=DataMaker.personal_info(user_data),
            expected_status_code=httpx.codes.CREATED,
            logger=logger,
            success_message=f"Created {common_message_part}",
            failure_message=f"Failed to create {common_message_part}",
            failure_logging_level=LoggingLevel.CRITICAL,
        )
        if data:
            logger.info(f"{data['id']=}")
            return typing.cast(int, data["id"])
        return 0
