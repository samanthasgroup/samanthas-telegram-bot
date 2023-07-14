from samanthas_telegram_bot.api_clients.base.exceptions import BaseApiClientError


class ChatwootClientError(BaseApiClientError):
    pass


class ChatwootJSONParsingError(ChatwootClientError):
    pass


class ChatwootRequestError(ChatwootClientError):
    pass
