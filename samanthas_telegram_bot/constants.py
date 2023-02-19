import re

from data.read_phrases import read_phrases

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

# UTC_TIME_SLOTS = ("05:00-08:00", "08:00-11:00", "11:00-14:00", "14:00-17:00", "17:00-21:00")
UTC_TIME_SLOTS = ((5, 8), (8, 11), (11, 14), (14, 17), (17, 21))
