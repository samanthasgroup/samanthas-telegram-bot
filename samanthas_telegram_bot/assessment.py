import csv

from samanthas_telegram_bot.constants import DATA_DIR, LANGUAGE_CODES


def get_questions(lang_code: str, level: str) -> tuple[dict[str, str], ...]:
    """Gets assessment questions, based on language and level"""
    if lang_code not in LANGUAGE_CODES:
        # There is a difference between no test being available (that shouldn't raise an error)
        # and a wrong language code being passed
        raise ValueError(f"Wrong language code {lang_code}")

    # TODO right now one test for all
    path_to_test = DATA_DIR / "assessment_temp.csv"

    with path_to_test.open(encoding="utf-8", newline="") as fh:
        rows = tuple(csv.DictReader(fh))

    return rows


if __name__ == "__main__":
    get_questions("en", "A1")
