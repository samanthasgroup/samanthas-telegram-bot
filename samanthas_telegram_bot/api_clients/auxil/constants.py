DataDict = dict[str, int | str | list[str] | list[int] | tuple[int, ...] | tuple[str, ...] | None]

API_URL_PREFIX = "https://admin.samanthasgroup.com/api"

API_URL_ENROLLMENT_TEST_GET_LEVEL = f"{API_URL_PREFIX}/enrollment_test_result/get_level/"
API_URL_ENROLLMENT_TEST_SEND_RESULT = f"{API_URL_PREFIX}/enrollment_test_result/"

API_URL_PERSONAL_INFO_LIST_CREATE = f"{API_URL_PREFIX}/personal_info/"

API_URL_STUDENT_RETRIEVE = f"{API_URL_PREFIX}/student/"
API_URL_STUDENTS_LIST_CREATE = f"{API_URL_PREFIX}/students/"

API_URL_TEACHER_RETRIEVE = f"{API_URL_PREFIX}/teacher/"
API_URL_TEACHERS_LIST_CREATE = f"{API_URL_PREFIX}/teachers/"

API_URL_YOUNG_TEACHER_RETRIEVE = f"{API_URL_PREFIX}/teacherunder18/"
API_URL_YOUNG_TEACHERS_LIST_CREATE = f"{API_URL_PREFIX}/teachers_under_18/"

API_URL_CHECK_EXISTENCE_OF_CHAT_ID = f"{API_URL_PREFIX}/personal_info/check_existence_of_chat_id/"
API_URL_CHECK_EXISTENCE_OF_PERSONAL_INFO = f"{API_URL_PREFIX}/personal_info/check_existence/"

API_URL_INFIX_DAY_AND_TIME_SLOTS = "day_and_time_slots"
API_URL_INFIX_ENROLLMENT_TESTS = "enrollment_test"
API_URL_INFIX_LANGUAGES_AND_LEVELS = "languages_and_levels"

MAX_ATTEMPTS_TO_GET_DATA_FROM_API = 10
SMALLTALK_URL_PREFIX = "https://app.smalltalk2.me/api/integration"
SMALLTALK_URL_GET_TEST = f"{SMALLTALK_URL_PREFIX}/send_test"
SMALLTALK_URL_GET_RESULTS = f"{SMALLTALK_URL_PREFIX}/test_status"
BASE_TIMEOUT_IN_SECS_BETWEEN_API_REQUEST_ATTEMPTS = 5
