from dataclasses import dataclass
from typing import Literal


@dataclass
class UserData:
    locale: str = None
    first_name: str = None
    last_name: str = None
    role: Literal["student", "teacher"] = None  # TODO Enum
    age: str = None  # it will be an age range
    source: str = None
    username: str = None
    phone_number: str = None
    email: str = None
    utc_offset: int = None
    levels_for_teaching_language: dict[str, list[str]] = None
    time_slots_for_day: dict = None
    student_communication_language: Literal["en", "ru", "ua"] = None
    has_prior_teaching_experience: bool = None
    teacher_number_of_groups: int = None
    class_frequency: int = None
    teacher_age_groups_of_students: list = None
