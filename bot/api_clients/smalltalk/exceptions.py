from bot.api_clients.base.exceptions import BaseApiClientError


class SmallTalkClientError(BaseApiClientError):
    pass


class SmallTalkRequestError(SmallTalkClientError):
    pass


class SmallTalkJSONParsingError(SmallTalkClientError):
    pass


class SmallTalkLogicError(SmallTalkClientError):
    pass
