import re
from typing import TYPE_CHECKING, Literal

from telegram.ext import CallbackContext, ExtBot

# Include custom classes into ContextTypes to get attribute hinting (replacing standard dicts with
# UserData for "user_data" etc.).
# If we import directly and include the custom types without ForwardRef's, we get circular import.
# If we only leave ForwardRefs and don't import with "if TYPE_CHECKING", we get no type hinting.

if TYPE_CHECKING:
    from samanthas_telegram_bot.conversation.data_structures.bot_data import BotData  # noqa
    from samanthas_telegram_bot.conversation.data_structures.chat_data import ChatData  # noqa
    from samanthas_telegram_bot.conversation.data_structures.user_data import UserData  # noqa
CUSTOM_CONTEXT_TYPES = CallbackContext[ExtBot[None], "UserData", "ChatData", "BotData"]


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

Locale = Literal["ua", "en", "ru"]
LOCALES: tuple[Locale, ...] = ("ua", "en", "ru")

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

STUDENT_COMMUNICATION_LANGUAGE_CODES: tuple[str, ...] = ("ru", "ua", "ru_ua", "l2_only")

TEACHER_PEER_HELP_TYPES = (
    "can_check_syllabus",
    "can_give_feedback",
    "can_help_with_children_group",
    "can_provide_materials",
    "can_host_mentoring_sessions",
    "can_invite_to_class",
    "can_work_in_tandem",
)
"""These types are used in `UserData`, callback data, setting boolean flags for teacher."""

UTC_TIME_SLOTS = ((5, 8), (8, 11), (11, 14), (14, 17), (17, 21))  # to make "05:00-08:00" etc.
