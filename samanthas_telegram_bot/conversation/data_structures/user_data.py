from dataclasses import dataclass
from typing import Literal

from samanthas_telegram_bot.conversation.data_structures.assessment import Assessment
from samanthas_telegram_bot.conversation.data_structures.constants import Locale
from samanthas_telegram_bot.conversation.data_structures.enums import Role


@dataclass
class AssessmentAnswer:
    # Those will be numbers, but both CallbackData and API work with strings,
    # and no math operations are performed, so no need to convert back and forth.
    question_id: str
    answer_id: str


@dataclass
class TeacherPeerHelp:
    """A class that comprises boolean flags for experienced teachers' willingness to help their
    peers.
    """

    can_consult_other_teachers: bool | None = None
    can_help_with_children_group: bool | None = None
    can_help_with_materials: bool | None = None
    can_check_syllabus: bool | None = None
    can_give_feedback: bool | None = None
    can_invite_to_class: bool | None = None
    can_work_in_tandem: bool | None = None


@dataclass
class UserData:
    # TODO sets instead of lists?
    locale: Locale | None = None
    first_name: str | None = None
    last_name: str | None = None
    source: str | None = None
    tg_username: str | None = None
    phone_number: str | None = None
    email: str | None = None
    role: Role | None = None
    # no datetime objects are needed to achieve results needed for the bot
    utc_offset_hour: int | None = None
    utc_offset_minute: int | None = None
    time_slots_for_day: dict | None = None  # type: ignore  # TODO use dataclass or TypedDict
    levels_for_teaching_language: dict[str, list[str]] | None = None
    communication_language_in_class: Literal["en", "ru", "ua"] | None = None
    # This will be a list as opposed to peer help that is a bunch of boolean flags, because IDs of
    # help types are fixed between back-end and bot anyway (they are used for bot phrases).
    non_teaching_help_types: list[str] | None = None
    comment: str | None = None

    # role-specific attributes:
    student_age_range_id: int | None = None  # for passing back to backend
    student_age_from: int | None = None  # for assessment
    student_age_to: int | None = None  # for assessment
    student_assessment: Assessment | None = None
    student_assessment_answers = list[AssessmentAnswer]
    student_can_read_in_english: bool | None = None
    # False instead of None is intended, because the value is set based on other answers.
    # By default, the student doesn't need an oral interview before they are included
    # in a waiting list for the group matching algorithm.
    student_needs_oral_interview: bool | None = False
    teacher_is_under_18: bool | None = None
    teacher_has_prior_experience: bool | None = None
    teacher_number_of_groups: int | None = None
    teacher_class_frequency: int | None = None
    teacher_student_age_range_ids: list[int] | None = None
    teacher_can_host_speaking_club: bool | None = None
    teacher_peer_help = TeacherPeerHelp()
    teacher_additional_skills_comment: str | None = None
