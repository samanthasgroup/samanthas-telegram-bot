import csv
from pathlib import Path


def read_phrases() -> dict[str, dict[str, str]]:
    """Reads bot phrases from CSV file, returns dictionary with internal IDs as key,
    and another dictionary as value, matching locales to actual phrases.
    """

    # for some strange reason another ".parent" doesn't work, but ".." does
    DATA_DIR = Path(__name__).parent / ".." / "data"

    with (DATA_DIR / "bot_phrases.csv").open(encoding="utf-8", newline="") as fh:
        rows = tuple(csv.DictReader(fh))

    return {
        row["internal_id"]: {locale: row[locale] for locale in ("en", "ru", "ua")} for row in rows
    }


if __name__ == "__main__":
    print(read_phrases())
