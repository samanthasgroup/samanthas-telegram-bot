from dataclasses import dataclass
from typing import Literal

from samanthas_telegram_bot.constants import Role


@dataclass
class TeacherPeerHelp:
    """A class that comprises boolean flags for experienced teachers' willingness to help their
    peers.
    """

    can_consult_other_teachers: bool = None
    can_help_with_children_group: bool = None
    can_help_with_materials: bool = None
    can_check_syllabus: bool = None
    can_give_feedback: bool = None
    can_invite_to_class: bool = None
    can_work_in_tandem: bool = None


@dataclass
class UserData:
    # TODO sets instead of lists?
    locale: str = None
    first_name: str = None
    last_name: str = None
    source: str = None
    tg_username: str = None
    phone_number: str = None
    email: str = None
    role: Role = None
    utc_offset: int = None
    time_slots_for_day: dict = None
    levels_for_teaching_language: dict[str, list[str]] = None
    communication_language_in_class: Literal["en", "ru", "ua"] = None
    # This will be a list as opposed to peer help that is a bunch of boolean flags, because IDs of
    # help types are fixed between back-end and bot anyway (they are used for bot phrases).
    non_teaching_help_types: list[str] = None
    comment: str = None

    # role-specific attributes:
    student_age_from: int = None
    student_age_to: int = None
    student_can_read_in_english: bool = None
    # False instead of None is intended, because the value is set based on other answers.
    # By default, the student doesn't need an oral interview before they are included
    # in a waiting list for the group matching algorithm.
    student_needs_oral_interview: bool = False
    teacher_is_under_18: bool = None
    teacher_has_prior_experience: bool = None
    teacher_number_of_groups: int = None
    teacher_class_frequency: int = None
    teacher_age_groups_of_students: list = None
    teacher_can_help_with_cv: bool = None  # FIXME remove
    teacher_can_host_speaking_club: bool = None
    teacher_peer_help = TeacherPeerHelp()
    teacher_additional_skills: list = None
    teacher_additional_skills_comment: str = None
