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


class ChatwootClient(BaseApiClient):
    @classmethod
    async def send_message_to_conversation(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        text: str,
    ) -> bool:
        """Sends a message to a conversation in Chatwoot.  Returns `True` if successful.

        Docs:

        * https://www.chatwoot.com/docs/product/channels/api/send-messages/ (overview)
        * https://www.chatwoot.com/developers/api/#tag/Messages/operation/create-a-new-message-in-a-conversation
        """
        conversation_id = context.user_data.helpdesk_conversation_id

        url = f"{CHATWOOT_URL_PREFIX}/conversations/{conversation_id}/messages"
        try:
            _, data = await cls.post(
                update=update,
                context=context,
                url=url,
                headers=CHATWOOT_HEADERS,
                json_data={
                    "content": text,
                    "message_type": "outgoing",  # FIXME create enum
                    # TODO content_type, content_attributes (not needed now, could be interesting)
                },
                notification_params_for_status_code={
                    httpx.codes.OK: NotificationParams(
                        "Received data: it is expected to contain `id` for sending messages "
                        "to this newly created Chatwoot conversation"
                    ),
                },
            )
        except BaseApiClientError as err:
            raise ChatwootRequestError(
                f"Failed to send message to conversation with {conversation_id=}"
            ) from err

        if not data:
            raise ChatwootJSONParsingError(
                f"Tried to send a message to Chatwoot {conversation_id=}. "
                "Status code is OK, but data is empty"
            )

        await logs(
            bot=context.bot,
            text=f"Successfully sent message to Chatwoot conversation {conversation_id}",
        )

        return True

    @classmethod
    async def start_new_conversation(
        cls,
        update: Update,
        context: CUSTOM_CONTEXT_TYPES,
        text: str,
    ) -> bool:
        """Creates contact in Chatwoot and starts new conversation. Returns `True` if successful.

        **Stores Chatwoot conversation ID in `context.user_data`**

        Steps as described in the docs:
        https://www.chatwoot.com/docs/product/channels/api/send-messages/

        1. Create contact
        2. Create conversation
        3. Send message to this conversation
        """
        user_data = context.user_data
        # TODO does conversation/some params depend on role?
        # TODO do I have to store chatwoot user ID as well?
        source_id = await cls._create_contact(update, context)
        user_data.helpdesk_conversation_id = await cls._start_conversation(
            update, context, source_id
        )
        return await cls.send_message_to_conversation(update, context, text=text)

    @classmethod
    async def _create_contact(cls, update: Update, context: CUSTOM_CONTEXT_TYPES) -> str:
        """Creates new contact in Chatwoot.

         Docs:

        * https://www.chatwoot.com/docs/product/channels/api/send-messages/ (overview)
        * https://www.chatwoot.com/developers/api/#operation/contactCreate
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
                    # FIXME I think I have to put chat ID elsewhere because this "identifier"
                    #  will not be unique in Chatwoot
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

    @classmethod
    async def _start_conversation(
        cls, update: Update, context: CUSTOM_CONTEXT_TYPES, source_id: str
    ) -> int:
        """Creates new conversation in Chatwoot and returns its ID.

        Docs:

        * https://www.chatwoot.com/docs/product/channels/api/send-messages/ (overview)
        * https://www.chatwoot.com/developers/api/#tag/Conversations/operation/newConversation
        """

        url = f"{CHATWOOT_URL_PREFIX}/conversations"
        try:
            _, data = await cls.post(
                update=update,
                context=context,
                url=url,
                headers=CHATWOOT_HEADERS,
                json_data={
                    "inbox_id": CHATWOOT_INBOX_ID,
                    "source_id": source_id,
                    # TODO contact_id? custom_attributes for conversation?
                    #  team_id will definitely be very useful, not sure about assignee_id.
                    "status": "pending",  # FIXME create enum + maybe "open" is more correct here
                },
                notification_params_for_status_code={
                    httpx.codes.OK: NotificationParams(
                        "Received data: it is expected to contain `id` for sending messages "
                        "to this newly created Chatwoot conversation"
                    ),
                },
            )
        except BaseApiClientError as err:
            raise ChatwootRequestError(
                "Failed to get data with conversation ID for the new conversation from Chatwoot"
            ) from err

        try:
            conversation_id = data["id"]  # type:ignore
        except KeyError as err:
            raise ChatwootJSONParsingError(f"Could not parse Chatwoot {data=}") from err

        await logs(
            bot=context.bot,
            text=f"Received ID of newly created Chatwoot conversation: {conversation_id}",
        )

        return typing.cast(int, conversation_id)
