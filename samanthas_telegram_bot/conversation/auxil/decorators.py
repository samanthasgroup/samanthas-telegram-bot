import functools
import logging
from collections.abc import Callable
from typing import Any

LOGGER = logging.getLogger(__name__)


def stay_in_same_state_if_update_has_no_message(
    func: Callable[[Any], Any]
) -> Callable[[Any], Any]:
    """Auxiliary decorator for staying in same conversation state when user sent no new message.

    It is impossible to send an empty message, but if for some reason user edits their previous
    message, an update will be issued, but .message attribute will be none.

    in this case, wait for user to type in the actual new message by returning him to the
    same state again, which is achieved by returning ``None``.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Callable[[Any], Any] | None:  # type:ignore[no-untyped-def]
        if args[0] is None or kwargs["update"].message is None:
            LOGGER.info("Update message is None, staying in the same conversation state.")
            return None
        return func(*args, **kwargs)

    return wrapper
