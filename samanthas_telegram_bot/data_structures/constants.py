"""Constants related to business logic and NOT imported from environment variables."""

import re

from samanthas_telegram_bot.data_structures.literal_types import Locale

# TODO Most of these could come from the backend to avoid duplicate changes, but that would mean
#  the bot phrases will have to be stored in the backend too (since e.g. non-teaching help types
#  are used to identify the phrases).
#  Maybe this can be changed anyway (not necessarily in MVP).
#  We could check ID's of phrases at the start to make sure there's no mismatch.
LOW_LEVELS = ("A0", "A1")
# Higher levels can technically pass oral test too, but it was decided not to send students to
# SmallTalk if their levels are too high for regular classes after "written" assessment.
LEVELS_ELIGIBLE_FOR_ORAL_TEST = ("A2", "B1")
LEVELS_TOO_HIGH = ("B2", "C1", "C2")
"""These levels mean that the student will only be able to attend Speaking Club sessions,
not regular classes."""
ALL_LEVELS = LOW_LEVELS + LEVELS_ELIGIBLE_FOR_ORAL_TEST + LEVELS_TOO_HIGH
# in reality, not all of these levels will be taught at the school but it's OK for the pattern
ALL_LEVELS_PATTERN = re.compile(r"^(A[012])|([BC][12])$")

ENGLISH: Locale = "en"
RUSSIAN: Locale = "ru"
UKRAINIAN: Locale = "ua"
LOCALES: tuple[Locale, ...] = (UKRAINIAN, ENGLISH, RUSSIAN)

LEARNED_FOR_YEAR_OR_MORE = "year_or_more"

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
