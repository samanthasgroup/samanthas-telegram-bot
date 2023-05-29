DataDict = dict[str, int | str | list[str] | list[int] | None]

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
