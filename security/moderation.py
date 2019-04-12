from anthill.platform.api.internal import connector
from typing import Union
import functools
import inspect


__all__ = ['moderated']


class ModerationError(Exception):
    def __init__(self, action_types, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action_types = action_types


async def _check_user_action_types(handler, required_action_types):
    get_moderations = functools.partial(
        connector.internal_request, 'moderation', 'get_moderations')
    user_moderations = await get_moderations(user_id=handler.current_user.id)
    user_action_types = set(m['action_type'] for m in user_moderations)
    shared_action_types = set(required_action_types) & user_action_types
    if shared_action_types:
        raise ModerationError(action_types=shared_action_types)


def moderated(action_types: Union[list, tuple]):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            await _check_user_action_types(args[0], action_types)
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator
