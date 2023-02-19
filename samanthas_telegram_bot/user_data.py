from dataclasses import dataclass
from typing import Literal


@dataclass
class UserData:
    locale: str = None
    first_name: str = None
    last_name: str = None
    role: Literal["student", "teacher"] = None
    age: str = None  # it will be an age range
    source: str = None
    username: str = None
    phone_number: str = None
    email: str = None
    utc_offset: int = None
    levels_for_teaching_language: dict = None
    time_slots_for_day: dict = None
