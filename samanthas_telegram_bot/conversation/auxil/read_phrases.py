import csv
from pathlib import Path


def read_phrases() -> dict[str, dict[str, str]]:
    """Reads bot phrases from CSV file, returns dictionary with internal IDs as key,
    and another dictionary as value, matching locales to actual phrases.
    """

    with (Path(__file__).parent.resolve() / "phrases.csv").open(encoding="utf-8", newline="") as f:
        rows = tuple(csv.DictReader(f))

    return {
        row["internal_id"]: {locale: row[locale] for locale in ("en", "ru", "ua")} for row in rows
    }


if __name__ == "__main__":
    print(read_phrases())
