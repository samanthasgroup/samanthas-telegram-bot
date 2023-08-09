import functools
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from telegram import Update

from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES

LOGGER = logging.getLogger(__name__)


async def stay_in_same_state_if_update_has_no_message(
    func: Callable[[Update, CUSTOM_CONTEXT_TYPES], Coroutine[Any, Any, int]]
) -> Any:
    """Auxiliary decorator for staying in same conversation state when user sent no new message.

    It is impossible to send an empty message, but if for some reason user edits their previous
    message, an update will be issued, but .message attribute will be none.

    in this case, wait for user to type in the actual new message by returning him to the
    same state again, which is achieved by returning ``None``.
    """

    @functools.wraps(func)
    async def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Any:
        # either first arg (update) or kwarg "update" has None in attribute "message"
        if getattr(args[0], "message") is None or getattr(kwargs["update"], "message") is None:
            LOGGER.info("Update message is None, staying in the same conversation state.")
            return None
        return func(*args, **kwargs)

    return wrapper
