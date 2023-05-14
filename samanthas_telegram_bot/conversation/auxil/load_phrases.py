import csv
import logging
import typing
from collections.abc import Iterator
from pathlib import Path

from samanthas_telegram_bot.conversation.data_structures.constants import LOCALES

logger = logging.getLogger(__name__)


def load_phrases() -> dict[str, dict[str, str]]:
    """Reads bot phrases from CSV file, returns dictionary with internal IDs as key,
    and another dictionary as value, matching locales to actual phrases.
    """

    logger.info("Loading bot phrases")
    with (Path(__file__).parent.resolve() / "phrases.csv").open(encoding="utf-8", newline="") as f:
        reader = typing.cast(Iterator[dict[str, str]], csv.DictReader(f))
        return {row["internal_id"]: {locale: row[locale] for locale in LOCALES} for row in reader}


if __name__ == "__main__":
    print(load_phrases())
