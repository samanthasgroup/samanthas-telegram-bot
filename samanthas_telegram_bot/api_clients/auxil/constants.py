import os
from typing import Any, cast

from dotenv import load_dotenv

load_dotenv()

DataDict = dict[
    # we have to put Any instead of "DataDict" ForwardRef,
    # a TypeError exception will be thrown otherwise
    str,
    int | str | list[str] | list[int] | tuple[int, ...] | tuple[str, ...] | Any | None,
]

API_URL_PREFIX = os.environ.get("BACKEND_API_URL_PREFIX")

API_URL_ENROLLMENT_TEST_GET_LEVEL = f"{API_URL_PREFIX}/enrollment_test_result/get_level/"
API_URL_ENROLLMENT_TEST_SEND_RESULT = f"{API_URL_PREFIX}/enrollment_test_result/"

API_URL_PREFIX_PERSONAL_INFO = f"{API_URL_PREFIX}/personal_info"
API_URL_PERSONAL_INFO_LIST_CREATE = f"{API_URL_PREFIX_PERSONAL_INFO}/"

API_URL_STUDENT_RETRIEVE = f"{API_URL_PREFIX}/student/"
API_URL_STUDENTS_LIST_CREATE = f"{API_URL_PREFIX}/students/"

API_URL_TEACHER_RETRIEVE = f"{API_URL_PREFIX}/teacher/"
API_URL_TEACHERS_LIST_CREATE = f"{API_URL_PREFIX}/teachers/"

API_URL_YOUNG_TEACHER_RETRIEVE = f"{API_URL_PREFIX}/teacherunder18/"
API_URL_YOUNG_TEACHERS_LIST_CREATE = f"{API_URL_PREFIX}/teachers_under_18/"

API_URL_CHECK_EXISTENCE_OF_CHAT_ID = f"{API_URL_PREFIX_PERSONAL_INFO}/check_existence_of_chat_id/"
API_URL_CHECK_EXISTENCE_OF_PERSONAL_INFO = f"{API_URL_PREFIX_PERSONAL_INFO}/check_existence/"

API_URL_INFIX_DAY_AND_TIME_SLOTS = "day_and_time_slots"
API_URL_INFIX_ENROLLMENT_TESTS = "enrollment_test"
API_URL_INFIX_LANGUAGES_AND_LEVELS = "languages_and_levels"

BASE_TIMEOUT_IN_SECS_BETWEEN_API_REQUEST_ATTEMPTS = 5
MAX_ATTEMPTS_TO_GET_DATA_FROM_API = 10

CHATWOOT_API_TOKEN = cast(str, os.environ.get("CHATWOOT_API_TOKEN"))
CHATWOOT_CUSTOM_ATTRIBUTE_CHAT_ID_IN_BOT = "chat_id_in_registration_bot"
CHATWOOT_HEADERS = {"api_access_token": CHATWOOT_API_TOKEN}
CHATWOOT_INBOX_ID = os.environ.get("CHATWOOT_INBOX_ID")
"""This ID defines the Chatwoot channel (inbox) that was created to exchange messages
between coordinators and users via this bot here.
See: https://www.chatwoot.com/docs/product/channels/api/create-channel/
"""
CHATWOOT_URL_PREFIX = os.environ.get("CHATWOOT_API_URL_PREFIX")

PERSON_EXISTENCE_CHECK_INVALID_EMAIL_MESSAGE_FROM_BACKEND = "Enter a valid email address"

SMALLTALK_RESULTING_LEVEL_UNDEFINED = "undefined"
SMALLTALK_URL_PREFIX = os.environ.get("SMALLTALK_URL_PREFIX")
SMALLTALK_URL_GET_TEST = f"{SMALLTALK_URL_PREFIX}/send_test"
SMALLTALK_URL_GET_RESULTS = f"{SMALLTALK_URL_PREFIX}/test_status"
SMALLTALK_TIMEOUT_IN_SECS_BETWEEN_API_REQUEST_ATTEMPTS = 30
