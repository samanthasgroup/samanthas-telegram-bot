# TODO for now this module only contains dummy functions
#  for the conversation flow to work.
import logging


async def chat_id_is_registered(chat_id: int, logger: logging.Logger) -> bool:
    """Checks whether the chat ID is already stored in the database."""
    logger.info(f"Checking with the backend if chat ID {chat_id} exists...")
    return False


async def person_with_first_name_last_name_email_exists_in_database(
    first_name: str,
    last_name: str,
    email: str,
    logger: logging.Logger,
) -> bool:
    """Checks whether user with given first and last name and email already exists in database."""
    logger.info(
        f"Checking with the backend if user {first_name} {last_name} ({email}) already exists."
    )
    return False
