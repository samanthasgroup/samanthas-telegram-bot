import logging
from enum import Enum


class ChatwootMessageDirection(str, Enum):
    FROM_CHATWOOT_TO_BOT = "outgoing"
    FROM_BOT_TO_CHATWOOT = "incoming"


class ChatwootUpdate:
    """Class for an update representing an incoming message from Chatwoot.

    Docs: https://www.chatwoot.com/docs/product/channels/api/receive-messages
    """

    def __init__(self, data: dict[str, dict[str, str] | str]):  # TODO not using user_id yet
        logger = logging.getLogger()  # FIXME remove?

        self.message = None

        if data["event"] == "message_created":
            top_key = "conversation"
            if data["message_type"] == ChatwootMessageDirection.FROM_CHATWOOT_TO_BOT:
                self.direction = ChatwootMessageDirection.FROM_CHATWOOT_TO_BOT
                self.message = data["content"]
            else:
                self.direction = ChatwootMessageDirection.FROM_BOT_TO_CHATWOOT
                # FIXME debug level
                logger.info(
                    "This is a message sent to Chatwoot from Bot. No need to show it to user."
                )
        else:
            top_key = "object"
            # skip handling of the update if this is not an update with a message
            # (e.g. some service update saying that a new conversation was created)

        # TODO maybe other message-related events will be needed too

        # When creating a Chatwoot contact, we stored their chat ID in the "identifier" attr.
        # It's time to use it now to identify which chat this update belongs to
        # Using this attribute name to conform with the `if update.message` check
        # FIXME maybe this data has to be moved to "custom_attributes" becuase otherwise
        #  identifier won't be unique
        self.chat_id = data[top_key]["meta"]["sender"]["identifier"]  # type:ignore[index]

        # FIXME maybe this attribute is not needed:
        self.bot_chat_id = data[top_key]["meta"]["sender"]["identifier"]  # type:ignore[index]

        self.chatwoot_conversation_id = data[top_key]["id"]  # type:ignore[index]

        # self.user_id = user_id  # TODO user_data will be none, but I don't need it now
        logger.info(f"{self.chat_id=}, {self.chatwoot_conversation_id=}, {data=}")  # FIXME debug

        # TODO do I need to check message_type for some reason?
        #  I may also want to use data["conversation"]["status"] (open or something else)
        #  In the future maybe we should support different "content_type". For now text only is OK.
