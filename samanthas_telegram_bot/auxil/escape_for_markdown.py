def escape_for_markdown(str_: str) -> str:
    escaped_str = str_
    for char in (
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
    ):
        escaped_str = escaped_str.replace(char, rf"\{char}")
    return escaped_str
