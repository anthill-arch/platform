from celery import Celery
from anthill.framework.conf import settings
from anthill.platform.core.celery.worker import start_worker
from anthill.platform.core.celery.loader import Loader

__all__ = ['app', 'start_worker']

SETTINGS = getattr(settings, 'CELERY_SETTINGS', {})

app_label = settings.APPLICATION_NAME.rpartition('.')[2]
default_entity_name = 'celery.%s' % app_label

SETTINGS.update({
    'task_default_queue': default_entity_name,
    'task_default_routing_key': default_entity_name,
    'task_default_exchange': default_entity_name,
    'imports': [
        '%s.tasks' % settings.APPLICATION_NAME,
    ]
})

app = Celery(main=app_label, loader=Loader)
app.conf.update(SETTINGS)
