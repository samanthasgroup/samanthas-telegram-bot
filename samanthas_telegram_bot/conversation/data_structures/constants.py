import re

from samanthas_telegram_bot.conversation.auxil.read_phrases import read_phrases

DAY_OF_WEEK_FOR_INDEX = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

DIGIT_PATTERN = re.compile(r"^\d+$")
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

STUDENT_COMMUNICATION_LANGUAGE_CODES: tuple[str, ...] = ("ru", "ua", "ru_ua", "l2_only")
UTC_TIME_SLOTS = ((5, 8), (8, 11), (11, 14), (14, 17), (17, 21))  # to make "05:00-08:00" etc.
