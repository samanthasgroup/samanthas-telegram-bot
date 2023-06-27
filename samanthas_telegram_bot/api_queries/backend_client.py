import logging
import os
import typing

import httpx
from telegram import Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.constants import (
    API_URL_CHECK_EXISTENCE_OF_CHAT_ID,
    API_URL_CHECK_EXISTENCE_OF_PERSONAL_INFO,
    API_URL_ENROLLMENT_TEST_GET_LEVEL,
    API_URL_ENROLLMENT_TEST_SEND_RESULT,
    API_URL_PERSONAL_INFO_LIST_CREATE,
    API_URL_STUDENT_RETRIEVE,
    API_URL_STUDENTS_LIST_CREATE,
    API_URL_TEACHER_RETRIEVE,
    API_URL_TEACHERS_LIST_CREATE,
    API_URL_YOUNG_TEACHER_RETRIEVE,
    API_URL_YOUNG_TEACHERS_LIST_CREATE,
    DataDict,
)
from samanthas_telegram_bot.api_queries.auxil.enums import HttpMethod, LoggingLevel
from samanthas_telegram_bot.api_queries.auxil.models import NotificationParams
from samanthas_telegram_bot.api_queries.base_api_client import BaseApiClient
from samanthas_telegram_bot.auxil.escape_for_markdown import escape_for_markdown
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import Role

logger = logging.getLogger(__name__)


class BackendClient(BaseApiClient):
    """Client for requests to the backend."""

    @classmethod
    async def chat_id_is_registered(cls, chat_id: int) -> bool:
        """Checks whether the chat ID is already stored in the database."""
        logger.info(f"Checking with the backend if chat ID {chat_id} exists...")

        response = await cls._make_async_request(
            method=HttpMethod.GET,
            url=API_URL_CHECK_EXISTENCE_OF_CHAT_ID,
            params={"registration_telegram_bot_chat_id": chat_id},
        )

        exists = response.status_code == httpx.codes.OK
        logger.info(f"... {chat_id} {exists=} ({response.status_code=})")
        return exists

    @classmethod
    async def create_student(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> bool:
        """Sends a POST request to create a student and send results of assessment if any.

        Returns `True` if successful.
        """

        personal_info_id = await cls._create_person(update, context)
        return await cls._send_student_assessment_results(
            update=update,
            context=context,
            personal_info_id=personal_info_id,
        )

    @classmethod
    async def create_adult_or_young_teacher(
        cls, update: Update, context: CUSTOM_CONTEXT_TYPES
    ) -> bool:
        """Sends a POST request to create teacher (adult or young).

        Returns `True` if successful.
        """
        return bool(await cls._create_person(update, context))

    @classmethod
    async def get_level_after_assessment(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
    ) -> str | None:
        """Sends answers to written assessment to the backend, gets level and returns it."""
        user_data = context.user_data

        answer_ids: tuple[int, ...] = tuple(
            item.answer_id for item in user_data.student_assessment_answers
        )
        number_of_questions = len(context.chat_data.assessment.questions)  # noqa

        await logs(
            bot=context.bot,
            level=LoggingLevel.INFO,
            text=(
                f"Chat {user_data.chat_id}: {len(answer_ids)} out of "
                f"{number_of_questions} questions were answered. Receiving level from backend..."
            ),
        )

        _, data = await cls.post(
            update=update,
            context=context,
            url=API_URL_ENROLLMENT_TEST_GET_LEVEL,
            data={"answers": answer_ids, "number_of_questions": number_of_questions},
            notification_params_for_status_code={
                httpx.codes.OK: NotificationParams(message="Checked result of written assessment"),
                httpx.codes.BAD_REQUEST: NotificationParams(
                    message="Failed to send results of written assessment and receive level",
                    logging_level=LoggingLevel.EXCEPTION,
                    notify_admins=True,
                ),
            },
        )

        try:
            level = typing.cast(str, data["resulting_level"])  # type: ignore[index]
        except KeyError:
            return None

        await logs(text=f"{level=}", bot=context.bot, update=update, level=LoggingLevel.INFO)
        return level

    @classmethod
    async def person_with_first_name_last_name_email_exists_in_database(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
    ) -> bool:
        """Checks whether user with given first and last name and email already exists in DB."""
        user_data = context.user_data
        first_name, last_name, email = user_data.first_name, user_data.last_name, user_data.email

        data_to_check = f"user {first_name} {last_name} ({email})"

        await logs(
            bot=context.bot,
            level=LoggingLevel.DEBUG,
            update=update,
            text=f"Checking with the backend if {data_to_check} already exists...",
        )
        status_code, data = await cls.post(
            update=update,
            context=context,
            url=API_URL_CHECK_EXISTENCE_OF_PERSONAL_INFO,
            data={"first_name": first_name, "last_name": last_name, "email": email},
            notification_params_for_status_code={
                httpx.codes.OK: NotificationParams(message=f"{data_to_check} does not exist"),
                httpx.codes.CONFLICT: NotificationParams(message=f"{data_to_check} exists"),
            },
        )

        return status_code == httpx.codes.CONFLICT

    @classmethod
    async def _create_person(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
        """Creates a person, returns their personal info ID."""
        personal_info_id = await cls._create_personal_info_get_id(update, context)
        url, data = cls._get_url_and_data_to_post(
            update=update,
            context=context,
            personal_info_id=personal_info_id,
        )

        status_code, _ = await cls.post(
            context=context,
            update=update,
            url=url,
            data=data,
            notification_params_for_status_code={
                httpx.codes.CREATED: NotificationParams(
                    message=cls._generate_success_message_for_person_creation(
                        context=context, personal_info_id=personal_info_id
                    ),
                    notify_admins=True,
                    parse_mode_for_bot_message=ParseMode.MARKDOWN_V2,
                ),
                httpx.codes.BAD_REQUEST: NotificationParams(
                    message=cls._generate_failure_message_for_person_creation(
                        context=context,
                        personal_info_id=personal_info_id,
                    ),
                    logging_level=LoggingLevel.EXCEPTION,
                    notify_admins=True,
                    parse_mode_for_bot_message=None,
                ),
            },
        )
        return personal_info_id

    @classmethod
    async def _create_personal_info_get_id(
        cls, update: Update, context: CUSTOM_CONTEXT_TYPES
    ) -> int:
        """Creates a personal info item and returns its ID."""
        user_data = context.user_data
        common_message_part = (
            f"personal data record for {user_data.first_name} "
            f"{user_data.last_name} ({user_data.email})"
        )
        failure_message = f"Failed to create {common_message_part}"

        _, data = await cls.post(
            context=context,
            update=update,
            url=API_URL_PERSONAL_INFO_LIST_CREATE,
            data=user_data.personal_info_as_dict(),
            notification_params_for_status_code={
                httpx.codes.CREATED: NotificationParams(
                    message=f"Created {common_message_part}",
                    notify_admins=True,
                ),
                httpx.codes.BAD_REQUEST: NotificationParams(
                    message=failure_message,
                    logging_level=LoggingLevel.EXCEPTION,
                    notify_admins=True,
                ),
            },
        )

        # for mypy
        if not isinstance(data, dict):
            raise TypeError(
                f"Received data of wrong type when creating a personal info item: {data=}"
            )

        personal_data_id = typing.cast(int, data["id"])

        await logs(
            bot=context.bot,
            update=update,
            level=LoggingLevel.INFO,
            text=f"Personal data ID: {personal_data_id}",
        )

        return personal_data_id

    @staticmethod
    def _get_url_and_data_to_post(
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        personal_info_id: int,
    ) -> tuple[str, DataDict]:
        """Returns url and data for a POST request depending on user data."""
        user_data = context.user_data
        if user_data.role not in (Role.STUDENT, Role.TEACHER):
            raise NotImplementedError(
                f"Cannot produce url and data to post: {user_data.role=} not supported."
            )

        if user_data.role == Role.STUDENT:
            return (
                API_URL_STUDENTS_LIST_CREATE,
                user_data.student_as_dict(update=update, personal_info_id=personal_info_id),
            )

        if user_data.role == Role.TEACHER and user_data.teacher_is_under_18:
            return (
                API_URL_YOUNG_TEACHERS_LIST_CREATE,
                user_data.teacher_under_18_as_dict(
                    update=update, personal_info_id=personal_info_id
                ),
            )

        return (
            API_URL_TEACHERS_LIST_CREATE,
            user_data.teacher_as_dict(update=update, personal_info_id=personal_info_id),
        )

    @staticmethod
    def _generate_failure_message_for_person_creation(
        context: CUSTOM_CONTEXT_TYPES, personal_info_id: int
    ) -> str:
        user_data = context.user_data
        teacher_age_infix = (
            "young " if user_data.role == Role.TEACHER and user_data.teacher_is_under_18 else ""
        )
        return f"Failed to create {teacher_age_infix}{user_data.role}, ID {personal_info_id}"

    @staticmethod
    def _generate_success_message_for_person_creation(
        context: CUSTOM_CONTEXT_TYPES, personal_info_id: int
    ) -> str:
        """Generates success message in Markdown V2 after a student/teacher was created."""
        user_data = context.user_data

        teacher_age_infix = (
            "young " if user_data.role == Role.TEACHER and user_data.teacher_is_under_18 else ""
        )

        if user_data.role == Role.TEACHER:
            url_prefix = (
                API_URL_YOUNG_TEACHER_RETRIEVE
                if user_data.teacher_is_under_18
                else API_URL_TEACHER_RETRIEVE
            )
        elif user_data == Role.STUDENT:
            url_prefix = API_URL_STUDENT_RETRIEVE
        else:
            raise NotImplementedError(f"{user_data.role=} not supported")

        success_message = (
            f"Created {teacher_age_infix}{user_data.role} "
            f"[{escape_for_markdown(user_data.first_name)} "
            f"{escape_for_markdown(user_data.last_name)}]"
            f"({url_prefix}{personal_info_id}), ID {personal_info_id}\\."
        )
        if user_data.role == Role.TEACHER and user_data.teacher_can_host_speaking_club:
            success_message += (
                f" @{os.environ.get('SPEAKING_CLUB_COORDINATOR_USERNAME')} "
                "this teacher can host speaking clubs\\."
            )

        return success_message

    @classmethod
    async def _send_student_assessment_results(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        personal_info_id: int,
    ) -> bool:
        user_data = context.user_data

        if not user_data.student_assessment_answers:
            await logs(
                bot=context.bot,
                level=LoggingLevel.INFO,
                update=update,
                text="No assessment answers to send",
            )
            return bool(personal_info_id)

        status_code, _ = await cls.post(
            update=update,
            context=context,
            url=API_URL_ENROLLMENT_TEST_SEND_RESULT,
            data=user_data.student_enrollment_test_as_dict(personal_info_id=personal_info_id),
            notification_params_for_status_code={
                httpx.codes.CREATED: NotificationParams(
                    f"Added assessment answers for {personal_info_id=}"
                ),
                httpx.codes.BAD_REQUEST: NotificationParams(
                    f"Failed to send written assessment for {personal_info_id=})",
                    logging_level=LoggingLevel.EXCEPTION,
                ),
            },
        )
        return status_code == httpx.codes.CREATED
