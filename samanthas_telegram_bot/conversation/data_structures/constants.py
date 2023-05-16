import re
from typing import Literal

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
