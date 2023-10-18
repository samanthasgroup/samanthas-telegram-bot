"""Auxiliary constants not related to business logic or imported from environment variables."""
import os
import re

from dotenv import load_dotenv

load_dotenv()

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
BOT_OWNER_USERNAME = os.environ.get("BOT_OWNER_USERNAME")
BOT_TECH_SUPPORT_USERNAME = os.environ.get("BOT_TECH_SUPPORT_USERNAME")

CALLER_LOGGING_STACK_LEVEL = 2
"""Stack level that will make the logger inside an auxiliary function display the name 
of function/method that called this helper function."""

EMAIL_PATTERN = re.compile(
    "(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+"
    "(?:\\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    '|"(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21\\x23-\\x5b\\x5d-\\x7f]'
    '|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])*")'
    "@"
    "(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z0-9]"
    "(?:[a-z0-9-]*[a-z0-9])?|\\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}"
    "(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?"
    "|[a-z0-9-]*[a-z0-9]:(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21-\\x5a\\x53-\\x7f]"
    "|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])+)\\])",
    re.IGNORECASE,
)

EXCEPTION_TRACEBACK_CLEANUP_PATTERN = re.compile(r"File .+/")  # it is intended to be greedy
"""Pattern to remove the long 'File:/path/to/file/' portion, but leave the file name."""

LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL")

PROJECT_STATUS_DEFAULT_AT_CREATION_STUDENT_TEACHER = "no_group_yet"
PROJECT_STATUS_DEFAULT_AT_CREATION_COORDINATOR = "pending"
PROJECT_STATUS_FOR_STUDENTS_THAT_NEED_INTERVIEW = "needs_interview_to_determine_level"

RUSSIAN_DOMAINS = (".ru", ".su", ".рф")

SPEAKING_CLUB_COORDINATOR_USERNAME = os.environ.get("SPEAKING_CLUB_COORDINATOR_USERNAME")

WEBHOOK_URL_PREFIX = os.environ.get("WEBHOOK_URL_PREFIX")
WEBHOOK_PATH_FOR_CHATWOOT = os.environ.get("WEBHOOK_PATH_FOR_CHATWOOT")
WEBHOOK_PATH_FOR_TELEGRAM = os.environ.get("WEBHOOK_PATH_FOR_TELEGRAM")

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
