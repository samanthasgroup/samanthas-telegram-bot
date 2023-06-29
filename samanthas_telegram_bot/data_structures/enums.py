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


class TeachingMode(str, Enum):
    """Enumeration for names of options that teacher can choose for their mode of work.

    Members of this enum can be treated as strings.
    """

    BOTH = "both"
    REGULAR_GROUPS_ONLY = "group"
    SPEAKING_CLUB_ONLY = "speaking_club"
