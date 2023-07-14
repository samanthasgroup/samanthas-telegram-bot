import logging
import typing

import httpx
from telegram import Update
from telegram.constants import ParseMode

from samanthas_telegram_bot.api_clients.auxil.constants import (
    API_URL_CHECK_EXISTENCE_OF_CHAT_ID,
    API_URL_CHECK_EXISTENCE_OF_PERSONAL_INFO,
    API_URL_ENROLLMENT_TEST_GET_LEVEL,
    API_URL_ENROLLMENT_TEST_SEND_RESULT,
    API_URL_GET_CHATWOOT_CONVERSATION_ID,
    API_URL_PERSONAL_INFO_LIST_CREATE,
    API_URL_STUDENT_RETRIEVE,
    API_URL_STUDENTS_LIST_CREATE,
    API_URL_TEACHER_RETRIEVE,
    API_URL_TEACHERS_LIST_CREATE,
    API_URL_YOUNG_TEACHER_RETRIEVE,
    API_URL_YOUNG_TEACHERS_LIST_CREATE,
    PERSON_EXISTENCE_CHECK_INVALID_EMAIL_MESSAGE_FROM_BACKEND,
    DataDict,
)
from samanthas_telegram_bot.api_clients.auxil.models import NotificationParams
from samanthas_telegram_bot.api_clients.backend.exceptions import BackendClientError
from samanthas_telegram_bot.api_clients.base.base_api_client import BaseApiClient
from samanthas_telegram_bot.api_clients.base.exceptions import BaseApiClientError
from samanthas_telegram_bot.auxil.constants import SPEAKING_CLUB_COORDINATOR_USERNAME
from samanthas_telegram_bot.auxil.escape_for_markdown import escape_for_markdown
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.data_structures.constants import ALL_LEVELS
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.enums import LoggingLevel, Role

logger = logging.getLogger(__name__)


class BackendClient(BaseApiClient):
    """Client for requests to the backend."""

    @classmethod
    async def chat_id_is_registered(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> bool:
        """Checks whether the chat ID is already stored in the backend."""
        chat_id = update.effective_chat.id

        await logs(
            bot=context.bot, update=update, text=f"Checking with backend if {chat_id=} exists..."
        )

        try:
            status_code, _ = await cls.get(
                update=update,
                context=context,
                url=API_URL_CHECK_EXISTENCE_OF_CHAT_ID,
                params={"registration_telegram_bot_chat_id": chat_id},
                notification_params_for_status_code={
                    httpx.codes.OK: NotificationParams(f"{chat_id=} already exists"),
                    httpx.codes.NOT_ACCEPTABLE: NotificationParams(f"{chat_id=} does not exist"),
                },
            )
        except BaseApiClientError as err:
            raise BackendClientError(f"Failed to check if {chat_id=} exists.") from err

        return status_code == httpx.codes.OK

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
    async def get_helpdesk_conversation_id(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
    ) -> int | None:
        """Gets Chatwoot conversation ID for this user by sending chat ID to the backend.

        Returns Chatwoot conversation ID or ``None`` if this no registration has yet occurred from
        this Telegram account and hence chat ID is not stored in the backend yet.
        """
        chat_id = context.user_data.chat_id

        try:
            _, data = await cls.get(
                update=update,
                context=context,
                url=API_URL_GET_CHATWOOT_CONVERSATION_ID,
                params={"registration_telegram_bot_chat_id": chat_id},
                notification_params_for_status_code={
                    httpx.codes.OK: NotificationParams(
                        message=f"Bot chat ID {chat_id} found. Received Chatwoot conversation ID"
                    ),
                    httpx.codes.NOT_ACCEPTABLE: NotificationParams(
                        message=(
                            f"No chat ID {chat_id} found. "
                            "This account is not registered in the backend"
                        )
                    ),
                },
            )
        except BaseApiClientError as err:
            raise BackendClientError("Failed to lookup Chatwoot conversation ID") from err

        chatwoot_conversation_id = typing.cast(int | None, data.get("chatwoot_conversation_id"))
        await logs(text=f"{chatwoot_conversation_id=}", bot=context.bot, update=update)
        return chatwoot_conversation_id

    @classmethod
    async def get_level_after_assessment(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
    ) -> str:
        """Sends answers to written assessment to the backend, gets level and returns it."""
        user_data = context.user_data

        answer_ids: tuple[int, ...] = tuple(
            item.answer_id for item in user_data.student_assessment_answers
        )
        number_of_questions = len(context.chat_data.assessment.questions)  # noqa

        await logs(
            bot=context.bot,
            text=(
                f"Chat {user_data.chat_id}: {len(answer_ids)} out of "
                f"{number_of_questions} questions were answered. Receiving level from backend..."
            ),
        )

        try:
            _, data = await cls.post(
                update=update,
                context=context,
                url=API_URL_ENROLLMENT_TEST_GET_LEVEL,
                data={"answers": answer_ids, "number_of_questions": number_of_questions},
                notification_params_for_status_code={
                    httpx.codes.OK: NotificationParams(
                        message="Checked result of written assessment"
                    ),
                },
            )
        except BaseApiClientError as err:
            raise BackendClientError(
                "Failed to send results of written assessment and receive level"
            ) from err

        level: str = cls._get_value(data, "resulting_level")
        if level not in ALL_LEVELS:
            raise BackendClientError(
                f"Received {level=} from backend that does not match any accepted level. {data=}"
            )

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

        try:
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
        except BaseApiClientError as err:
            if PERSON_EXISTENCE_CHECK_INVALID_EMAIL_MESSAGE_FROM_BACKEND in str(err):
                raise BackendClientError(
                    f"{PERSON_EXISTENCE_CHECK_INVALID_EMAIL_MESSAGE_FROM_BACKEND} "
                    f"({email} is invalid)"
                ) from err
            raise BackendClientError(f"Failed to check existence of {data_to_check=}") from err

        return status_code == httpx.codes.CONFLICT

    @classmethod
    async def _create_person(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> int:
        """Creates a person, returns their personal info ID.

        Type of person to be created is determined based on ``context``.
        """
        personal_info_id = await cls._create_personal_info_get_id(update, context)
        # FIXME send message to Chatwoot, get chatwoot conversation ID
        url, data = cls._get_url_and_data_for_person_creation(
            update=update,
            context=context,
            personal_info_id=personal_info_id,
        )

        try:
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
                },
            )
        except BaseApiClientError as err:
            raise BackendClientError(
                cls._generate_failure_message_for_person_creation(
                    context=context,
                    personal_info_id=personal_info_id,
                ),
            ) from err

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

        try:
            _, data = await cls.post(
                context=context,
                update=update,
                url=API_URL_PERSONAL_INFO_LIST_CREATE,
                data=user_data.personal_info_as_dict(),
                notification_params_for_status_code={
                    httpx.codes.CREATED: NotificationParams(
                        message=f"Created {common_message_part}",
                    ),
                },
            )
        except BaseApiClientError as err:
            raise BackendClientError(f"Failed to create {common_message_part}") from err

        # for mypy
        if not isinstance(data, dict):
            raise TypeError(
                f"Received data of wrong type when creating a personal info item: {data=}"
            )

        personal_data_id = typing.cast(int, data["id"])

        await logs(
            bot=context.bot,
            update=update,
            text=f"Personal data ID: {personal_data_id}",
        )

        return personal_data_id

    @staticmethod
    def _get_url_and_data_for_person_creation(
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        personal_info_id: int,
    ) -> tuple[str, DataDict]:
        """Returns url and data for a POST request to create a person, based on user data."""
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
        elif user_data.role == Role.STUDENT:
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
                f" @{SPEAKING_CLUB_COORDINATOR_USERNAME} this teacher can host speaking clubs\\."
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
                update=update,
                text="No assessment answers to send",
            )
            return bool(personal_info_id)

        try:
            status_code, _ = await cls.post(
                update=update,
                context=context,
                url=API_URL_ENROLLMENT_TEST_SEND_RESULT,
                data=user_data.student_enrollment_test_as_dict(personal_info_id=personal_info_id),
                notification_params_for_status_code={
                    httpx.codes.CREATED: NotificationParams(
                        f"Added assessment answers for {personal_info_id=}"
                    ),
                },
            )
        except BaseApiClientError as err:
            raise BackendClientError(
                f"Failed to send written assessment for {personal_info_id=})"
            ) from err

        # return True would have the same effect, but this is more explicit
        return status_code == httpx.codes.CREATED

    @classmethod
    def _get_value(cls, data: DataDict, key: str) -> typing.Any:
        try:
            return super()._get_value(data, key)
        except BaseApiClientError as err:
            raise BackendClientError("Failed to process data received from backend") from err
