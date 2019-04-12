from anthill.platform.services.update.backends.base import BaseUpdateManager
from pip import _internal as pip_internal
from typing import List, Optional
import logging


class PipUpdateManager(BaseUpdateManager):
    async def has_updates(self):
        pass

    async def versions(self) -> List[str]:
        pass

    async def current_version(self) -> str:
        pass

    async def check_updates(self) -> List[str]:
        pass

    async def update(self, version: Optional[str] = None) -> None:
        pass
