from celery.loaders.base import BaseLoader
import logging

logger = logging.getLogger('anthill.application')


class Loader(BaseLoader):
    def on_task_init(self, task_id, task):
        """Called before a task is executed."""

    def on_process_cleanup(self):
        """Called after a task is executed."""

    def on_worker_init(self):
        """Called when the worker (:program:`celery worker`) starts."""

    def on_worker_shutdown(self):
        """Called when the worker (:program:`celery worker`) shuts down."""

    def on_worker_process_init(self):
        """Called when a child process starts."""

    def import_task_module(self, module):
        try:
            super().import_task_module(module)
        except ModuleNotFoundError:
            logger.error('Celery tasks module `%s` not found.' % module)
