from enum import Enum, IntEnum, auto


class AgeRangeType(str, Enum):
    """Enumeration types of age ranges. Members of this enum can be treated as strings."""

    MATCHING = "matching"
    STUDENT = "student"
    TEACHER = "teacher"


class CommonCallbackData(str, Enum):
    """Enumeration for fixed values of callback_data. Members of this enum can be treated as
    strings.
    """

    DONE = "done"
    NEXT = "next"
    NO = "no"
    OK = "ok"
    YES = "yes"


class ConversationMode(str, Enum):
    """Enumeration for chat modes: normal or review mode (when user reviews personal info)."""

    NORMAL = "normal"
    REVIEW = "review"


class ConversationState(IntEnum):
    """Provides integer keys for the dictionary of states for ConversationHandler."""

    IS_REGISTERED = auto()
    CHECK_CHAT_ID_ASK_FIRST_NAME = auto()
    CHECK_IF_WANTS_TO_REGISTER_ANOTHER_PERSON_ASK_FIRST_NAME = auto()
    ASK_LAST_NAME = auto()
    ASK_SOURCE = auto()
    CHECK_USERNAME = auto()
    ASK_PHONE_NUMBER = auto()
    ASK_EMAIL = auto()
    ASK_ROLE = auto()
    ASK_AGE = auto()
    ASK_TIMEZONE = auto()
    TIME_SLOTS_START = auto()
    TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE = auto()
    ASK_LEVEL_OR_ANOTHER_TEACHING_LANGUAGE_OR_COMMUNICATION_LANGUAGE = auto()
    ASK_LEVEL_OR_COMMUNICATION_LANGUAGE = auto()
    ASK_TEACHING_EXPERIENCE = auto()
    ASK_TEACHING_GROUP_OR_SPEAKING_CLUB = auto()
    ADOLESCENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_ASSESSMENT = auto()
    ASK_STUDENT_NON_TEACHING_HELP_OR_START_REVIEW = auto()
    ASK_ASSESSMENT_QUESTION = auto()
    SEND_SMALLTALK_URL_OR_ASK_COMMUNICATION_LANGUAGE = auto()
    ASK_COMMUNICATION_LANGUAGE_AFTER_SMALLTALK = auto()
    ASK_NUMBER_OF_GROUPS_OR_TEACHING_FREQUENCY_OR_NON_TEACHING_HELP = auto()
    ASK_TEACHING_FREQUENCY = auto()
    PREFERRED_STUDENT_AGE_GROUPS_START = auto()
    PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP = auto()
    NON_TEACHING_HELP_MENU_OR_PEER_HELP_FOR_TEACHER_OR_REVIEW_FOR_STUDENT = auto()
    PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP = auto()
    ASK_YOUNG_TEACHER_ADDITIONAL_HELP = auto()
    ASK_REVIEW = auto()
    REVIEW_MENU_OR_ASK_FINAL_COMMENT = auto()
    REVIEW_REQUESTED_ITEM = auto()
    ASK_FINAL_COMMENT = auto()  # standalone, not after review
    BYE = auto()


class Role(str, Enum):
    """Role of a person. Members of this enum can be treated as strings."""

    STUDENT = "student"
    TEACHER = "teacher"


class TeachingMode(str, Enum):
    """Enumeration for names of options that teacher can choose for their mode of work.

    Members of this enum can be treated as strings.
    """

    BOTH = "both"
    REGULAR_GROUPS_ONLY = "group"
    SPEAKING_CLUB_ONLY = "speaking_club"


class UserDataReviewCategory(str, Enum):
    """Enumeration for names of options that user can choose when reviewing their data.

    Members of this enum can be treated as strings.
    """

    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    STUDENT_AGE_GROUP = "student_age_group"
    TIMEZONE = "timezone"
    AVAILABILITY = "availability"
    LANGUAGE_AND_LEVEL = "language_and_level"
    CLASS_COMMUNICATION_LANGUAGE = "class_communication_language"
