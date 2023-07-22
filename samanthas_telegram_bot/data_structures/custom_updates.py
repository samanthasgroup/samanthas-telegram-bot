class ChatwootUpdate:
    """Class for an update representing an incoming message from Chatwoot.

    Docs: https://www.chatwoot.com/docs/product/channels/api/receive-messages
    """

    def __init__(self, data: dict[str, dict[str, str] | str]):
        self.conversation_id = data["conversation"]["id"]  # type:ignore[index]
        # FIXME add exception handling

        # Using this attribute name to conform with the `if update.message` check
        # TODO maybe rework that logic and rename this attribute
        self.message = data["content"]

        # TODO do I need to check message_type for some reason?
        #  I may also want to use data["conversation"]["status"] (open or something else)
        #  In the future maybe we should support different "content_type". For now text only is OK.
