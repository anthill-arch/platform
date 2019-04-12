from anthill.framework.auth.models import AnonymousUser
from anthill.platform.core.messenger.exceptions import NotAuthenticatedError
from functools import wraps


def auth_required(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        user = self.client.user
        if isinstance(user, (type(None), AnonymousUser)):
            raise NotAuthenticatedError('Authentication required')
        return await func(self, *args, **kwargs)

    return wrapper


def action(**kwargs):
    def decorator(func):
        func.action = True
        func.kwargs = kwargs
        return func

    return decorator
