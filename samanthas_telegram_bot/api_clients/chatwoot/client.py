"""Functions for interaction with Chatwoot helpdesk."""
import logging
import os
import typing

import httpx
from dotenv import load_dotenv
from telegram import Update

from samanthas_telegram_bot.api_clients.auxil.constants import (
    CHATWOOT_HEADERS,
    CHATWOOT_INBOX_ID,
    CHATWOOT_URL_PREFIX,
    SMALLTALK_RESULTING_LEVEL_UNDEFINED,
    SMALLTALK_URL_GET_RESULTS,
    DataDict,
)
from samanthas_telegram_bot.api_clients.auxil.enums import SmalltalkTestStatus
from samanthas_telegram_bot.api_clients.auxil.models import NotificationParams
from samanthas_telegram_bot.api_clients.base.base_api_client import BaseApiClient
from samanthas_telegram_bot.api_clients.base.exceptions import BaseApiClientError
from samanthas_telegram_bot.api_clients.chatwoot.exceptions import (
    ChatwootJSONParsingError,
    ChatwootRequestError,
)
from samanthas_telegram_bot.api_clients.smalltalk.exceptions import (
    SmallTalkJSONParsingError,
    SmallTalkLogicError,
    SmallTalkRequestError,
)
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.data_structures.constants import ALL_LEVELS
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES
from samanthas_telegram_bot.data_structures.models import SmalltalkResult

load_dotenv()
logger = logging.getLogger(__name__)

HEADERS = {"Authorization": f"Bearer {os.environ.get('SMALLTALK_TOKEN')}"}
ORAL_TEST_ID = os.environ.get("SMALLTALK_TEST_ID")


# TODO no working code here yet
class ChatwootClient(BaseApiClient):
    @classmethod
    async def create_contact_and_conversation(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
    ) -> None:
        """Creates contact in Chatwoot and starts new conversation.

        Steps as described in the docs:
        https://www.chatwoot.com/docs/product/channels/api/send-messages/

        1. Create contact
        2. Create conversation
        3. Send message to this conversation
        """
        # TODO does conversation/some params depend on role?
        # TODO do I have to store chatwoot user ID as well?
        await cls._create_conversation(update, context)

    @classmethod
    async def _create_conversation(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> str:
        """Creates new contact in Chatwoot.

        Docs: https://www.chatwoot.com/developers/api/#operation/contactCreate
        """
        user_data = context.user_data

        url = f"{CHATWOOT_URL_PREFIX}/contacts"
        try:
            _, data = await cls.post(
                update=update,
                context=context,
                url=url,
                headers=CHATWOOT_HEADERS,
                json_data={
                    "inbox_id": CHATWOOT_INBOX_ID,
                    "name": f"{user_data.first_name} {user_data.last_name}",
                    "email": user_data.email,
                    "phone": user_data.phone_number,
                    # TODO "identifier"?
                    # TODO just testing attributes. TG username is probably not needed. Age? Level?
                    "custom_attributes": {
                        "Telegram": user_data.tg_username
                    },  # FIXME it's flat-typed
                },
                notification_params_for_status_code={
                    httpx.codes.OK: NotificationParams(
                        "Received data that should contain source_id for the new chat in Chatwoot"
                    ),
                },
            )
        except BaseApiClientError as err:
            raise ChatwootRequestError(
                "Failed to get data with source_id for the new chat from Chatwoot"
            ) from err

        try:
            source_id = data["payload"]["contact_inbox"]["source_id"]  # type:ignore  # TODO
        except KeyError as err:
            raise ChatwootJSONParsingError(f"Could not parse Chatwoot {data=}") from err

        await logs(bot=context.bot, text=f"Received source_id from Chatwoot: {source_id}")

        return typing.cast(str, source_id)

    @classmethod
    async def _get_data(
        cls, update: Update, context: CUSTOM_CONTEXT_TYPES, test_id: str
    ) -> DataDict:
        user_data = context.user_data

        try:
            _, data = await cls.get(
                update=update,
                context=context,
                url=SMALLTALK_URL_GET_RESULTS,
                headers=HEADERS,
                params={
                    "id": test_id,
                    "additional_fields": (
                        "detailed_scores,strength_weaknesses,problem_statuses,problem_titles"
                    ),
                },
                notification_params_for_status_code={
                    httpx.codes.OK: NotificationParams(
                        # The data may not contain the results yet, we're just logging
                        # that status code was 200 OK and hence some data was received
                        f"Received data from SmallTalk after {user_data.first_name} "
                        f"{user_data.last_name}'s test"
                    )
                },
            )
        except BaseApiClientError as err:
            raise SmallTalkRequestError(
                "Failed to receive valid response from SmallTalk while getting test results."
            ) from err

        return data

    @classmethod
    async def _process_data(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        data: DataDict,
    ) -> SmalltalkResult:
        status_name = cls._get_value(data, "status")
        try:
            status = SmalltalkTestStatus(status_name)
        except ValueError as err:
            raise SmallTalkLogicError(
                f"SmallTalk returned status '{status_name}' but we have no logic for it."
            ) from err

        if status == SmalltalkTestStatus.NOT_STARTED_OR_IN_PROGRESS:
            await logs(
                bot=context.bot, update=update, text="User has not yet completed the interview"
            )
        elif status == SmalltalkTestStatus.RESULTS_NOT_READY:
            await logs(
                bot=context.bot,
                update=update,
                text="User has completed the interview but the results are not ready",
            )

        if status != SmalltalkTestStatus.RESULTS_READY:
            return SmalltalkResult(status)

        level: str = cls._get_value(data, "score")
        level = level.strip()

        # 1. Strip off "p" in "B2p" and the like
        # 2. We use capital letters in our levels, so convert for easier comparison
        level_id = level.removesuffix("p").upper()

        if level.lower() == SMALLTALK_RESULTING_LEVEL_UNDEFINED:
            await logs(
                bot=context.bot,
                update=update,
                text="User did not pass enough oral tasks for level to be determined",
            )
            level_id = ""
        elif level_id not in ALL_LEVELS:
            raise SmallTalkJSONParsingError(f"Unrecognized language level returned: {level}")

        results_url = cls._get_value(data, "report_url")

        await logs(
            bot=context.bot,
            update=update,
            text=f"SmallTalk results: {status=}, {level=}, {results_url=}",
        )

        return SmalltalkResult(
            status=status,
            level=level_id,
            url=results_url,
            json=data,
        )

    @classmethod
    def _get_value(cls, data: DataDict, key: str) -> typing.Any:
        # TODO this will only work for flat structure
        try:
            return super()._get_value(data, key)
        except BaseApiClientError as err:
            raise ChatwootJSONParsingError(f"Could not parse Chatwoot {data=}") from err
