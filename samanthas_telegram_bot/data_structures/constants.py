import re
from typing import Literal

# TODO Most of these could come from the backend to avoid duplicate changes, but that would mean
#  the bot phrases will have to be stored in the backend too (since e.g. non-teaching help types
#  are used to identify the phrases).
#  Maybe this can be changed anyway (not necessarily in MVP).
#  We could check ID's of phrases at the start to make sure there's no mismatch.

EMAIL_PATTERN = re.compile(r"^([a-zA-Z_\-.]+)@([a-zA-Z_\-.]+)\.([a-zA-Z]{2,5})$")

LOW_LEVELS = ("A0", "A1")
LEVELS_ELIGIBLE_FOR_ORAL_TEST = ("A2", "B1", "B2", "C1", "C2")
ALL_LEVELS = LOW_LEVELS + LEVELS_ELIGIBLE_FOR_ORAL_TEST

Locale = Literal["ua", "en", "ru"]
LOCALES: tuple[Locale, ...] = ("ua", "en", "ru")

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
