from anthill.framework.conf import settings
from anthill.framework.utils.module_loading import import_string
from anthill.platform.services.update.exceptions import UpdateError
from anthill.framework.utils.asynchronous import as_future
from typing import Optional
import logging
import os


logger = logging.getLogger('anthill.application')


UPDATES_SETTINGS = getattr(settings, 'UPDATES', {})
UPDATE_MANAGER = UPDATES_SETTINGS.get(
    'MANAGER', 'anthill.platform.services.update.backends.git.GitUpdateManager')


class UpdateManager:
    def __init__(self):
        self.manager = import_string(UPDATE_MANAGER)()

    async def update(self, version: Optional[str] = None):
        await self.update_system_requirements()
        await self.update_pip_requirements()
        await self.update_service(version)

    async def update_service(self, version):
        await self.manager.update(version)
        logger.info('Service has been updated successfully.')

    @as_future
    def update_pip_requirements(self):
        from pip import _internal
        req_file = os.path.join(settings.BASE_DIR, 'requirements.txt')
        _internal.main(['install', '-r', req_file])
        logger.info('Pip requirements installed successfully.')

    @as_future
    def update_system_requirements(self):
        logger.info('System requirements installed successfully.')
