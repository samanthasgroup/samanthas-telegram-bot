from enum import Enum


class HttpMethod(str, Enum):
    # http.HTTPMethod only comes in Python 3.11, plus we need those to be in lowercase,
    GET = "get"
    POST = "post"
    # TODO enhance


class SmalltalkTestStatus(str, Enum):
    """Enumeration of possible statuses of a SmallTalk oral test, returned by its API."""

    NOT_STARTED_OR_IN_PROGRESS = "sent"  # meaning "link to interview was sent to user"
    RESULTS_NOT_READY = "processing"
    RESULTS_READY = "completed"
