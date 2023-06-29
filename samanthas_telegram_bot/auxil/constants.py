import os

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
BOT_OWNER_USERNAME = os.environ.get("BOT_OWNER_USERNAME")
CHARACTERS_TO_BE_ESCAPED_IN_MARKDOWN: tuple[str, ...] = (
    "\\",
    "`",
    "*",
    "_",
    "{",
    "}",
    "[",
    "]",
    "<",
    ">",
    "(",
    ")",
    "#",
    "+",
    "-",
    ".",
    "!",
    "|",
    "=",
)

LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL")
SPEAKING_CLUB_COORDINATOR_USERNAME = os.environ.get("SPEAKING_CLUB_COORDINATOR_USERNAME")
