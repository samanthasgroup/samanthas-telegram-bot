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
)
from samanthas_telegram_bot.api_clients.auxil.models import NotificationParams
from samanthas_telegram_bot.api_clients.base.base_api_client import BaseApiClient
from samanthas_telegram_bot.api_clients.base.exceptions import BaseApiClientError
from samanthas_telegram_bot.api_clients.chatwoot.exceptions import (
    ChatwootJSONParsingError,
    ChatwootRequestError,
)
from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES

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
                    # A Chatwoot conversation can only be linked to user's Telegram account,
                    # not to their ID in the database.
                    # This is because several users can share one Telegram account.
                    "identifier": user_data.chat_id,
                    # TODO just testing attributes. TG username is probably not needed. Age? Level?
                    "custom_attributes": {"Telegram": user_data.tg_username},
                },
                notification_params_for_status_code={
                    httpx.codes.OK: NotificationParams(
                        "Received data: it is expected to contain `source_id` for the new chat "
                        "in Chatwoot"
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
