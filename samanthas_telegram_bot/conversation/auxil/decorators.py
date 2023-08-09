import functools
from collections.abc import Callable
from typing import Any

from telegram import Update

from samanthas_telegram_bot.auxil.log_and_notify import logs
from samanthas_telegram_bot.data_structures.context_types import CUSTOM_CONTEXT_TYPES


async def stay_in_same_state_if_update_has_no_message(
    update: Update, context: CUSTOM_CONTEXT_TYPES
) -> Callable[[Any], Any] | None:
    """Auxiliary decorator for staying in same conversation state when user sent no new message.

    It is impossible to send an empty message, but if for some reason user edits their previous
    message, an update will be issued, but .message attribute will be none.

    in this case, wait for user to type in the actual new message by returning him to the
    same state again, which is achieved by returning ``None``.
    """

    # TODO an enhancement could be to store the information from the edited message
    if update.message is None:
        await logs(bot=context.bot, update=update, text="No new message, staying in same state")
        return None

    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Callable[[Any], Any]:  # type:ignore[no-untyped-def]
            return func(*args, **kwargs)

        return wrapper

    return decorator
