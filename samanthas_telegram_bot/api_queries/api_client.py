import logging
import os
import typing
from typing import Any

import httpx
from httpx import Response
from telegram import Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_queries.auxil.constants import (
    API_URL_CHECK_EXISTENCE_OF_CHAT_ID,
    API_URL_CHECK_EXISTENCE_OF_PERSONAL_INFO,
    API_URL_ENROLLMENT_TEST_GET_LEVEL,
    API_URL_ENROLLMENT_TEST_SEND_RESULT,
    API_URL_PERSONAL_INFO_LIST_CREATE,
    API_URL_PREFIX,
    API_URL_STUDENT_RETRIEVE,
    API_URL_STUDENTS_LIST_CREATE,
    API_URL_TEACHER_RETRIEVE,
    API_URL_TEACHERS_LIST_CREATE,
    API_URL_YOUNG_TEACHER_RETRIEVE,
    API_URL_YOUNG_TEACHERS_LIST_CREATE,
    DataDict,
)
from samanthas_telegram_bot.api_queries.auxil.enums import (
    HttpMethod,
    LoggingLevel,
    SendToAdminGroupMode,
)
from samanthas_telegram_bot.api_queries.auxil.exceptions import ApiRequestError
from samanthas_telegram_bot.auxil.escape_for_markdown import escape_for_markdown
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import Role

LOGGER = logging.getLogger(__name__)


class ApiClient:
    """Client for requests to the backend."""

    # TODO make it universal (for SmallTalk too)?
    # TODO make sure we catch wrong status, empty JSON etc.

    @classmethod
    async def chat_id_is_registered(cls, chat_id: int) -> bool:
        """Checks whether the chat ID is already stored in the database."""
        LOGGER.info(f"Checking with the backend if chat ID {chat_id} exists...")

        response = await cls._make_async_request(
            method=HttpMethod.GET,
            url=API_URL_CHECK_EXISTENCE_OF_CHAT_ID,
            params={"registration_telegram_bot_chat_id": chat_id},
        )

        exists = response.status_code == httpx.codes.OK
        LOGGER.info(f"... {chat_id} {exists=} ({response.status_code=})")
        return exists

    @classmethod
    async def create_student(
        cls, update: Update, context: CUSTOM_CONTEXT_TYPES  # type: ignore[valid-type]
    ) -> bool:
        """Sends a POST request to create a student and send results of assessment if any."""

        personal_info_id = await cls._create_personal_info_get_id(context)
        user_data = context.user_data  # type: ignore[attr-defined]

        result = await cls._send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_STUDENTS_LIST_CREATE,
            data=user_data.student_as_dict(update=update, personal_info_id=personal_info_id),
            expected_status_code=httpx.codes.CREATED,
            success_message=cls._generate_success_message_for_person_creation(
                context=context, personal_info_id=personal_info_id
            ),
            failure_message=f"Failed to create student with ID {personal_info_id}",
            failure_logging_level=LoggingLevel.CRITICAL,
            notify_admins_mode=SendToAdminGroupMode.SUCCESS_AND_FAILURE,
            parse_mode_for_admin_group_message=ParseMode.MARKDOWN_V2,
        )

        if not user_data.student_assessment_answers:
            await logs(
                bot=context.bot,  # type:ignore[attr-defined]
                level=LoggingLevel.INFO,
                update=update,
                text="No assessment answers to send",
            )
            return result is not None

        result = await cls._send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_ENROLLMENT_TEST_SEND_RESULT,
            data=user_data.student_enrollment_test_as_dict(personal_info_id=personal_info_id),
            expected_status_code=httpx.codes.CREATED,
            success_message=f"Added assessment answers for {personal_info_id=}",
            failure_message=f"Failed to send written assessment for {personal_info_id=})",
            failure_logging_level=LoggingLevel.CRITICAL,
            parse_mode_for_admin_group_message=ParseMode.MARKDOWN_V2,
        )
        return result is not None

    @classmethod
    async def create_teacher(
        cls, update: Update, context: CUSTOM_CONTEXT_TYPES  # type: ignore[valid-type]
    ) -> bool:
        """Sends a POST request to create an adult teacher."""

        personal_info_id = await cls._create_personal_info_get_id(context)
        user_data = context.user_data  # type: ignore[attr-defined]

        result = await cls._send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_TEACHERS_LIST_CREATE,
            data=user_data.teacher_as_dict(update=update, personal_info_id=personal_info_id),
            expected_status_code=httpx.codes.CREATED,
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
    async def create_teacher_under_18(
        cls, update: Update, context: CUSTOM_CONTEXT_TYPES  # type: ignore[valid-type]
    ) -> bool:
        """Sends a POST request to create a teacher under 18 years old."""

        personal_info_id = await cls._create_personal_info_get_id(context)
        user_data = context.user_data  # type: ignore[attr-defined]

        result = await cls._send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_YOUNG_TEACHERS_LIST_CREATE,
            data=user_data.teacher_under_18_as_dict(
                update=update, personal_info_id=personal_info_id
            ),
            expected_status_code=httpx.codes.CREATED,
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
    def get_json(
        url_infix: str,
        name_for_logger: str | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Function for simple synchronous GET requests with logging."""
        if not name_for_logger:
            name_for_logger = url_infix.replace("_", " ")

        LOGGER.info(f"Getting {name_for_logger} from the backend...")

        # synchronous requests are only run at application startup, so no exception handling needed
        response = httpx.get(f"{API_URL_PREFIX}/{url_infix}/", params=params)

        data = response.json()
        LOGGER.info(f"...received {len(data)} {name_for_logger}.")

        return data

    @classmethod
    async def get_level_of_written_test(
        cls,
        context: CUSTOM_CONTEXT_TYPES,  # type: ignore[valid-type]
    ) -> str | None:
        """Sends answers to written assessment to the backend, gets level and returns it."""
        user_data = context.user_data  # type: ignore[attr-defined]

        answer_ids: tuple[int, ...] = tuple(
            item.answer_id for item in user_data.student_assessment_answers
        )
        number_of_questions = len(context.chat_data.assessment.questions)  # type: ignore[attr-defined]  # noqa

        await logs(
            bot=context.bot,  # type:ignore[attr-defined]
            level=LoggingLevel.INFO,
            text=(
                f"Chat {user_data.chat_id}: {len(answer_ids)} out of "
                f"{number_of_questions} questions were answered. Receiving level from backend..."
            ),
        )

        data = await cls._send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_ENROLLMENT_TEST_GET_LEVEL,
            data={"answers": answer_ids, "number_of_questions": number_of_questions},
            expected_status_code=httpx.codes.OK,
            success_message="Checked result of written assessment",
            failure_message="Failed to send results of written assessment and receive level",
            failure_logging_level=LoggingLevel.CRITICAL,
            notify_admins_mode=SendToAdminGroupMode.FAILURE_ONLY,
        )

        try:
            level = typing.cast(str, data["resulting_level"])  # type: ignore[index]
        except KeyError:
            return None

        LOGGER.info(f"{level=}")
        return level

    @classmethod
    async def person_with_first_name_last_name_email_exists_in_database(
        cls,
        first_name: str,
        last_name: str,
        email: str,
    ) -> bool:
        """Checks whether user with given first and last name and email already exists in DB."""
        data_to_check = f"user {first_name} {last_name} ({email})"

        LOGGER.info(f"Checking with the backend if {data_to_check} already exists...")
        response = await cls._make_async_request(
            method=HttpMethod.POST,
            url=API_URL_CHECK_EXISTENCE_OF_PERSONAL_INFO,
            data={"first_name": first_name, "last_name": last_name, "email": email},
        )

        # this is correct: `exists` is False if status is 200 OK
        exists = response.status_code != httpx.codes.OK
        LOGGER.info(f"... {data_to_check} {exists=} ({response.status_code=}, {response.json()=})")
        return exists

    @classmethod
    async def _create_personal_info_get_id(
        cls, context: CUSTOM_CONTEXT_TYPES  # type: ignore[valid-type]
    ) -> int:
        """Creates a personal info item and returns its ID."""
        user_data = context.user_data  # type: ignore[attr-defined]
        common_message_part = (
            f"personal data record for {user_data.first_name} "
            f"{user_data.last_name} ({user_data.email})"
        )
        failure_message = f"Failed to create {common_message_part}"

        data = await cls._send_to_backend(
            context=context,
            method=HttpMethod.POST,
            url=API_URL_PERSONAL_INFO_LIST_CREATE,
            data=user_data.personal_info_as_dict(),
            expected_status_code=httpx.codes.CREATED,
            success_message=f"Created {common_message_part}",
            failure_message=failure_message,
            failure_logging_level=LoggingLevel.CRITICAL,
        )
        if data:
            LOGGER.info(f"{data['id']=}")
            return typing.cast(int, data["id"])
        raise ApiRequestError(failure_message)

    @staticmethod
    def _generate_success_message_for_person_creation(
        context: CUSTOM_CONTEXT_TYPES, personal_info_id: int  # type: ignore[valid-type]
    ) -> str:
        user_data = context.user_data  # type: ignore[attr-defined]

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
            f"[{user_data.first_name} {user_data.last_name}]"
            f"({url_prefix}{personal_info_id}), ID {personal_info_id}\\."
        )
        if user_data.role == Role.TEACHER and user_data.teacher_can_host_speaking_club:
            success_message += (
                f" @{os.environ.get('SPEAKING_CLUB_COORDINATOR_USERNAME')} "
                "this teacher can host speaking clubs\\."
            )

        return success_message

    @staticmethod
    async def _make_async_request(
        method: HttpMethod, url: str, data: DataDict | None = None, params: DataDict | None = None
    ) -> Response:
        async with httpx.AsyncClient() as client:
            if method == HttpMethod.GET:
                return await client.get(url, params=params)
            elif method == HttpMethod.POST:
                return await client.post(url, params=params, data=data)
            else:
                raise NotImplementedError(f"{method=} not supported")

    @classmethod
    async def _send_to_backend(
        cls,
        context: CUSTOM_CONTEXT_TYPES,  # type: ignore[valid-type]
        method: HttpMethod,
        url: str,
        data: DataDict,
        expected_status_code: int,
        success_message: str,
        failure_message: str,
        success_logging_level: LoggingLevel = LoggingLevel.INFO,
        failure_logging_level: LoggingLevel = LoggingLevel.ERROR,
        notify_admins_mode: SendToAdminGroupMode = SendToAdminGroupMode.FAILURE_ONLY,
        parse_mode_for_admin_group_message: ParseMode | None = None,
    ) -> DataDict | None:
        """Sends a request to backend, returns data, logs and notifies admins of potential errors.

        Returns data received from backend in response.

        This method is supposed to be called from within a chat (e.g. from a callback that has
        a context object passed to it).
        """
        response = await cls._make_async_request(method=method, url=url, data=data)

        message_prefix = f"Chat {context.user_data.chat_id}: "  # type: ignore[attr-defined]
        message_suffix = ""
        failure_message_suffix = (
            f"{message_suffix} {response.status_code=} {response.json()=} {response.content=} "
            f"@{os.environ.get('BOT_OWNER_USERNAME')}"
        )

        if parse_mode_for_admin_group_message == ParseMode.MARKDOWN_V2:
            message_prefix = escape_for_markdown(message_prefix)
            message_suffix = escape_for_markdown(message_suffix)
            failure_message_suffix = escape_for_markdown(failure_message_suffix)

        if response.status_code != expected_status_code:
            await logs(
                bot=context.bot,  # type: ignore[attr-defined]
                level=failure_logging_level,
                text=f"{message_prefix}{failure_message}{failure_message_suffix}",
                needs_to_notify_admin_group=notify_admins_mode
                in (SendToAdminGroupMode.FAILURE_ONLY, SendToAdminGroupMode.SUCCESS_AND_FAILURE),
                parse_mode_for_admin_group_message=parse_mode_for_admin_group_message,
            )
            return None

        await logs(
            bot=context.bot,  # type: ignore[attr-defined]
            level=success_logging_level,
            text=f"{message_prefix}{success_message}{message_suffix}",
            needs_to_notify_admin_group=notify_admins_mode
            in (SendToAdminGroupMode.SUCCESS_ONLY, SendToAdminGroupMode.SUCCESS_AND_FAILURE),
            parse_mode_for_admin_group_message=parse_mode_for_admin_group_message,
        )

        try:
            response_json = response.json()
        except AttributeError as e:
            exc_info = f" {e}"
            if parse_mode_for_admin_group_message == ParseMode.MARKDOWN_V2:
                failure_message_suffix += escape_for_markdown(exc_info)
            else:
                failure_message_suffix += exc_info
            return None
        else:
            LOGGER.debug(f"Response JSON: {response_json}")
            return response_json
