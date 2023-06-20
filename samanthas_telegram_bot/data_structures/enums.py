from enum import Enum


class AgeRangeType(str, Enum):
    """Enumeration types of age ranges. Members of this enum can be treated as strings."""

    MATCHING = "matching"
    STUDENT = "student"
    TEACHER = "teacher"


class Role(str, Enum):
    """Role of a person. Members of this enum can be treated as strings."""

    STUDENT = "student"
    TEACHER = "teacher"


class SmalltalkTestStatus(str, Enum):
    """Enumeration of possible statuses of a SmallTalk oral test, returned by its API."""

    NOT_STARTED_OR_IN_PROGRESS = "sent"  # meaning "link to interview was sent to user"
    RESULTS_NOT_READY = "processing"
    RESULTS_READY = "completed"


class TeachingMode(str, Enum):
    """Enumeration for names of options that teacher can choose for their mode of work.

    Members of this enum can be treated as strings.
    """

    BOTH = "both"
    REGULAR_GROUPS_ONLY = "group"
    SPEAKING_CLUB_ONLY = "speaking_club"
