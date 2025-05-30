import logging
from enum import Enum

from bot.api_clients.auxil.constants import CHATWOOT_CUSTOM_ATTRIBUTE_CHAT_ID_IN_BOT

logger = logging.getLogger(__name__)


class ChatwootMessageDirection(str, Enum):
    FROM_CHATWOOT_TO_BOT = "outgoing"
    FROM_BOT_TO_CHATWOOT = "incoming"


class ChatwootUpdate:
    """Class for an update representing an incoming message from Chatwoot.

    Docs: https://www.chatwoot.com/docs/product/channels/api/receive-messages
    """

    def __init__(self, data: dict[str, dict[str, str] | str]):
        # Using this attribute name to conform with the `if update.message` check
        # TODO maybe it's knowing too much and is worth refactoring
        self.message = None

        if data["event"] == "message_created":
            top_key = "conversation"
            if data["message_type"] == ChatwootMessageDirection.FROM_CHATWOOT_TO_BOT:
                self.direction = ChatwootMessageDirection.FROM_CHATWOOT_TO_BOT
                self.message = data["content"]
            else:
                self.direction = ChatwootMessageDirection.FROM_BOT_TO_CHATWOOT
                logger.debug(
                    "This is a message sent to Chatwoot from Bot. No need to show it to user."
                )
        else:
            top_key = "object"
            # skip handling of the update if this is not an update with a message
            # (e.g. some service update saying that a new conversation was created)

        # TODO maybe other message-related events will be needed too

        # When creating a Chatwoot contact, we stored their chat ID.
        # It's time to use it now to identify which chat this update belongs to
        self.chat_id = data[top_key]["meta"]["sender"]["custom_attributes"][  # type:ignore[index]
            CHATWOOT_CUSTOM_ATTRIBUTE_CHAT_ID_IN_BOT  # type:ignore[index]
        ]

        self.chatwoot_conversation_id = data[top_key]["id"]  # type:ignore[index]

        logger.debug(f"{self.chat_id=}, {self.chatwoot_conversation_id=}, {data=}")

        # TODO do I need to check message_type for some reason?
        #  I may also want to use data["conversation"]["status"] (open or something else)
        #  In the future maybe we should support different "content_type". For now text only is OK.
