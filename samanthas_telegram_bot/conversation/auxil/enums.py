from enum import Enum


class CommonCallbackData(str, Enum):
    """Enumeration for fixed values of callback_data. Members of this enum can be treated as
    strings.
    """

    ABORT = "abort"
    DONE = "done"
    NEXT = "next"
    NO = "no"
    OK = "ok"
    YES = "yes"


class ConversationMode(str, Enum):
    """Enumeration for chat modes: normal or review mode (when user reviews personal info)."""

    NORMAL = "normal"
    REVIEW = "review"


class UserDataReviewCategory(str, Enum):
    """Enumeration for names of options that user can choose when reviewing their data.

    Members of this enum can be treated as strings.
    """

    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    STUDENT_AGE_GROUP = "student_age_group"
    TIMEZONE = "timezone"
    AVAILABILITY = "availability"
    LANGUAGE_AND_LEVEL = "language_and_level"
    CLASS_COMMUNICATION_LANGUAGE = "class_communication_language"
