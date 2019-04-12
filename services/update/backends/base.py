from typing import List, Optional


class BaseUpdateManager:
    async def has_updates(self) -> bool:
        raise NotImplementedError

    async def versions(self) -> List[str]:
        raise NotImplementedError

    async def current_version(self) -> str:
        raise NotImplementedError

    async def latest_version(self) -> str:
        raise NotImplementedError

    async def check_updates(self) -> List[str]:
        raise NotImplementedError

    async def update(self, version: Optional[str] = None) -> None:
        raise NotImplementedError
