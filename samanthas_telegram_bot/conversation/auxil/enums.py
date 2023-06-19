from enum import Enum, IntEnum


class CommonCallbackData(str, Enum):
    """Enumeration for fixed values of callback_data. Members of this enum can be treated as
    strings.
    """

    ABORT = "abort"
    DONE = "done"
    NEXT = "next"
    NO = "no"
    OK = "ok"
    YES = "yes"


class ConversationMode(str, Enum):
    """Enumeration for chat modes: normal or review mode (when user reviews personal info)."""

    NORMAL = "normal"
    REVIEW = "review"


state_index = 0


def state_auto() -> int:
    """A replacement for enum.auto() that allows to create integer indexes for multiple classes.

    Running enum.auto() in every `...State` IntEnum will start at 1.
    This simple implementation with a global variable lets us continue where previous enum ended.
    """
    global state_index
    state_index += 1
    return state_index


class ConversationStateCommon(IntEnum):
    """Provides integer keys for the dictionary of common states for ConversationHandler."""

    IS_REGISTERED = state_auto()
    CHECK_CHAT_ID_ASK_TIMEZONE = state_auto()
    CHECK_IF_WANTS_TO_REGISTER_ANOTHER_PERSON_ASK_TIMEZONE = state_auto()
    ASK_FIRST_NAME = state_auto()
    ASK_LAST_NAME = state_auto()
    ASK_SOURCE = state_auto()
    CHECK_USERNAME = state_auto()
    ASK_PHONE_NUMBER = state_auto()
    ASK_EMAIL = state_auto()
    ASK_ROLE = state_auto()
    ASK_AGE = state_auto()
    TIME_SLOTS_MENU_OR_ASK_TEACHING_LANGUAGE = state_auto()
    ASK_REVIEW = state_auto()
    REVIEW_MENU_OR_ASK_FINAL_COMMENT = state_auto()
    REVIEW_REQUESTED_ITEM = state_auto()
    ASK_FINAL_COMMENT = state_auto()  # standalone, not after review
    BYE = state_auto()


class ConversationStateStudent(IntEnum):
    """Provides integer keys for the dictionary of student's states for ConversationHandler."""

    ADOLESCENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_TEST = state_auto()
    ASK_QUESTION_IN_TEST = state_auto()
    ASK_COMMUNICATION_LANGUAGE_AFTER_SMALLTALK = state_auto()
    ASK_LEVEL_OR_COMMUNICATION_LANGUAGE_OR_START_TEST = state_auto()
    ENGLISH_STUDENTS_ASK_COMMUNICATION_LANGUAGE_OR_START_TEST_DEPENDING_ON_ABILITY_TO_READ = (
        state_auto()
    )
    ASK_NON_TEACHING_HELP_OR_START_REVIEW = state_auto()
    ASK_SLOTS_OR_TEACHING_LANGUAGE = state_auto()
    NON_TEACHING_HELP_MENU_OR_REVIEW = state_auto()
    SEND_SMALLTALK_URL_OR_ASK_COMMUNICATION_LANGUAGE = state_auto()
    TIME_SLOTS_START = state_auto()


class ConversationStateTeacher(IntEnum):
    """Provides integer keys for the dictionary of teacher's states for ConversationHandler."""

    ASK_LEVEL_OR_ANOTHER_LANGUAGE_OR_COMMUNICATION_LANGUAGE = state_auto()
    ASK_NUMBER_OF_GROUPS_OR_FREQUENCY_OR_NON_TEACHING_HELP = state_auto()
    ASK_SLOTS_OR_TEACHING_LANGUAGE = state_auto()
    ASK_TEACHING_EXPERIENCE = state_auto()
    ASK_TEACHING_FREQUENCY = state_auto()
    ASK_TEACHING_GROUP_OR_SPEAKING_CLUB = state_auto()
    ASK_YOUNG_TEACHER_ADDITIONAL_HELP = state_auto()
    ASK_YOUNG_TEACHER_COMMUNICATION_LANGUAGE = state_auto()
    ASK_YOUNG_TEACHER_SPEAKING_CLUB_LANGUAGE = state_auto()
    NON_TEACHING_HELP_MENU_OR_PEER_HELP = state_auto()
    PEER_HELP_MENU_OR_ASK_ADDITIONAL_HELP = state_auto()
    PREFERRED_STUDENT_AGE_GROUPS_START = state_auto()
    PREFERRED_STUDENT_AGE_GROUPS_MENU_OR_ASK_NON_TEACHING_HELP = state_auto()
    TIME_SLOTS_START_OR_ASK_YOUNG_TEACHER_ABOUT_SPEAKING_CLUB = state_auto()


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
