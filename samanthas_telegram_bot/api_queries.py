# TODO for now this module only contains dummy functions
#  for the conversation flow to work.
import logging


async def chat_id_is_registered(chat_id: int, logger: logging.Logger) -> bool:
    """Checks whether the chat ID is already stored in the database."""
    logger.info(f"Checking with the backend if chat ID {chat_id} exists...")
    return False
