import logging


class ChatwootUpdate:
    """Class for an update representing an incoming message from Chatwoot.

    Docs: https://www.chatwoot.com/docs/product/channels/api/receive-messages
    """

    def __init__(self, data: dict[str, dict[str, str] | str]):
        logger = logging.getLogger()  # TODO remove
        logger.info(data)

        if data["event"] != "message_created":
            # skip handling of the update if this is not an update with a message
            # (e.g. some service update saying that a new conversation was created)
            self.message = None
            return

        self.chatwoot_conversation_id = data["conversation"]["id"]  # type:ignore[index]
        # FIXME add exception handling

        # When creating a Chatwoot contact, we stored their chat ID in the "identifier" attribute.
        # It's time to use it now to identify which chat this update belongs to
        self.bot_chat_id = data["conversation"]["meta"]["sender"][  # type:ignore[index]  # noqa
            "identifier"  # type:ignore[index]
        ]
        # Using this attribute name to conform with the `if update.message` check
        # TODO maybe rework that logic and rename this attribute
        self.message = data["content"]

        # TODO do I need to check message_type for some reason?
        #  I may also want to use data["conversation"]["status"] (open or something else)
        #  In the future maybe we should support different "content_type". For now text only is OK.
