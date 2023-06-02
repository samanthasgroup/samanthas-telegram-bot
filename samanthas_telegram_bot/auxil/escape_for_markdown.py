from samanthas_telegram_bot.auxil.constants import CHARACTERS_TO_BE_ESCAPED_IN_MARKDOWN


def escape_for_markdown(str_: str) -> str:
    escaped_str = str_
    for char in CHARACTERS_TO_BE_ESCAPED_IN_MARKDOWN:
        escaped_str = escaped_str.replace(char, rf"\{char}")
    return escaped_str
