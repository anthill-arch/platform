from anthill.framework.core.cache import caches
from anthill.framework.handlers.base import BaseClientsWatcher

__all__ = ['CacheClientsWatcher', 'MessengerClientsWatcher']


class CacheClientsWatcher(BaseClientsWatcher):
    user_limit: int = 0
    storage = caches['websocket_clients_watcher']

    def __init__(self, user_limit: int = 0):
        if user_limit:
            self.user_limit = user_limit
        self.handlers = {}

    def build_cache_key(self, handler):
        return ':'.join([id(handler), self.get_user_id(handler)])

    async def append(self, handler) -> None:
        user_id = self.get_user_id(handler)
        self.handlers.setdefault(user_id, []).append(handler)

    async def remove(self, handler) -> None:
        user_id = self.get_user_id(handler)
        self.handlers[user_id].remove(handler)

    async def count(self) -> int:
        raise NotImplementedError

    def get_user_id(self, handler) -> str:
        return handler.current_user.id


class MessengerClientsWatcher(CacheClientsWatcher):
    """Messenger handlers watcher."""

    async def count(self) -> int:
        raise NotImplementedError
