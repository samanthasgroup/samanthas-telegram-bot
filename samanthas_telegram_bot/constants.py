import re
from enum import Enum

from data.read_phrases import read_phrases


class CallbackData(str, Enum):
    """Enumeration for fixed values of callback_data. Members of this enum can be treated as
    strings.
    """

    DONE = "done"
    NEXT = "next"
    NO = "no"
    YES = "yes"


class Role(str, Enum):
    """Role of a person. Members of this enum can be treated as strings."""

    STUDENT = "student"
    TEACHER = "teacher"


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
PHONE_PATTERN = re.compile(r"^(\+)|(00)[1-9][0-9]{1,14}$")
PHRASES = read_phrases()
# Teacher-oriented age groups are in here because they are used in several modules
STUDENT_AGE_GROUPS_FOR_TEACHER = {
    "children": "6-11",
    "adolescents": "12-17",
    "adults": "18-",
}
STUDENT_COMMUNICATION_LANGUAGE_CODES = ("ru", "ua", "ru_ua", "l2_only")
UTC_TIME_SLOTS = ((5, 8), (8, 11), (11, 14), (14, 17), (17, 21))  # to make "05:00-08:00" etc.
