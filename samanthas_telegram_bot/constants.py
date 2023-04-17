import re
from enum import Enum
from pathlib import Path

from data.read_phrases import read_phrases


class CallbackData(str, Enum):
    """Enumeration for fixed values of callback_data. Members of this enum can be treated as
    strings.
    """

    DONE = "done"
    DONT_KNOW = "don't know"
    NEXT = "next"
    NO = "no"
    OK = "ok"
    YES = "yes"


class ChatMode(str, Enum):
    """Enumeration for chat modes: normal or review mode (when user reviews personal info)."""

    NORMAL = "normal"
    REVIEW = "review"


class UserDataReviewCategory(str, Enum):
    """Enumeration for names of options that user can choose when reviewing their data at the end
    of the registration process. Members of this enum can be treated as strings.
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


class Role(str, Enum):
    """Role of a person. Members of this enum can be treated as strings."""

    STUDENT = "student"
    TEACHER = "teacher"


# for some strange reason another ".parent" doesn't work, but ".." does
DATA_DIR = Path(__name__).parent / ".." / "data"

DAY_OF_WEEK_FOR_INDEX = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

EMAIL_PATTERN = re.compile(r"^([\w\-.]+)@([\w\-.]+)\.([a-zA-Z]{2,5})$")

# TODO maybe factor out from phrases; addition of language will require double changes
LANGUAGE_CODES = ("en", "fr", "de", "es", "it", "pl", "cz", "se")
LEVELS = ("A0", "A1", "A2", "B1", "B2", "C1")
LOCALES = ("ua", "en", "ru")

# these could come from the backend, but that would mean the bot phrases will have to be stored
# in the backend too (since these types are used to identify the phrases)
NON_TEACHING_HELP_TYPES = (
    "cv_write_edit",
    "cv_proofread",
    "mock_interview",
    "job_search",
    "career_strategy",
    "linkedin",
    "career_switch",
    "portfolio",
    "uni_abroad",
    "translate_docs",
)

PHRASES = read_phrases()  # TODO move function to this package

# Teacher-oriented age groups are in here because they are used in several modules
# FIXME everything should come from the backend?
STUDENT_AGE_GROUPS_FOR_TEACHER = {
    "children": "5-12",
    "adolescents": "13-17",
    "adults": "18-65",
    "seniors": "66-95",
}
STUDENT_COMMUNICATION_LANGUAGE_CODES = ("ru", "ua", "ru_ua", "l2_only")
UTC_TIME_SLOTS = ((5, 8), (8, 11), (11, 14), (14, 17), (17, 21))  # to make "05:00-08:00" etc.
