from enum import Enum


class HttpMethod(str, Enum):
    # http.HTTPMethod only comes in Python 3.11, plus we need those to be in lowercase,
    GET = "get"
    POST = "post"
    # TODO enhance


class LoggingLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EXCEPTION = "exception"
