"""Embedded workers for integration"""
import threading
from contextlib import contextmanager
from celery import worker, shared_task, Celery
from celery.result import allow_join_result, _set_task_join_will_block
from celery.utils.dispatch import Signal
from celery.utils.nodenames import anon_nodename
from celery.worker.consumer import Consumer
from typing import Iterable, Any, Union

worker_starting = Signal(
    name='worker_starting',
    providing_args={},
)
worker_started = Signal(
    name='worker_started',
    providing_args={'worker', 'consumer'},
)
worker_stopped = Signal(
    name='worker_stopped',
    providing_args={'worker'},
)


class WorkController(worker.WorkController):
    """Worker that can synchronize on being fully started."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._on_started = threading.Event()
        super(WorkController, self).__init__(*args, **kwargs)

    def on_consumer_ready(self, consumer: Consumer) -> None:
        """Callback called when the Consumer blueprint is fully started."""
        self._on_started.set()
        worker_started.send(sender=self.app, worker=self, consumer=consumer)

    def ensure_started(self) -> None:
        """Wait for worker to be fully up and running.

        Warning:
            Worker must be started within a thread for this to work,
            or it will block forever.
        """
        self._on_started.wait()


@shared_task(name='celery.ping')
def ping() -> str:
    """Simple task that just returns 'pong'."""
    return 'pong'


@contextmanager
def start_worker(app: Celery,
                 concurrency: int = None,
                 pool: str = None,
                 loglevel: Union[str, int] = None,
                 logfile: str = None,
                 perform_ping_check: bool = True,
                 ping_task_timeout: float = 10.0,
                 **kwargs: Any) -> Iterable:
    """Start embedded worker.

    Yields:
        celery.app.worker.Worker: worker instance.
    """
    worker_starting.send(sender=app)

    with _start_worker_thread(app,
                              concurrency=concurrency,
                              pool=pool,
                              loglevel=loglevel,
                              logfile=logfile,
                              **kwargs) as _worker:
        if perform_ping_check:
            with allow_join_result():
                assert ping.delay().get(timeout=ping_task_timeout) == 'pong'

        yield _worker
    worker_stopped.send(sender=app, worker=worker)


@contextmanager
def _start_worker_thread(app: Celery,
                         concurrency: int = None,
                         pool: str = None,
                         loglevel: Union[str, int] = None,
                         logfile: str = None,
                         work_controller: Any = WorkController,
                         **kwargs: Any) -> Iterable:
    """Start Celery worker in a thread.

    Yields:
        celery.worker.Worker: worker instance.
    """
    setup_app_for_worker(app, loglevel, logfile)
    assert 'celery.ping' in app.tasks

    # Make sure we can connect to the broker
    with app.connection() as conn:
        conn.default_channel.queue_declare

    _worker = work_controller(
        app=app,
        concurrency=concurrency,
        hostname=anon_nodename(),
        pool=pool,
        loglevel=loglevel,
        logfile=logfile,
        # not allowed to override WorkController.on_consumer_ready
        ready_callback=None,
        without_heartbeat=True,
        without_mingle=True,
        without_gossip=True,
        **kwargs)

    t = threading.Thread(target=_worker.start)
    t.start()
    _worker.ensure_started()
    _set_task_join_will_block(False)

    yield _worker

    from celery.worker import state
    state.should_terminate = 0
    # t.join(10)
    state.should_terminate = None


@contextmanager
def _start_worker_process(app: Celery,
                          concurrency: int = 1,
                          pool: str = 'solo',
                          loglevel: Union[int, str] = 'info',
                          logfile: str = None,
                          **kwargs: Any) -> Iterable:
    """Start worker in separate process.

    Yields:
        celery.app.worker.Worker: worker instance.
    """
    from celery.apps.multi import Cluster, Node

    app.set_current()
    cluster = Cluster([Node('worker@%h')])
    cluster.start()
    yield
    cluster.stopwait()


def setup_app_for_worker(app: Celery, loglevel: Union[str, int], logfile: str) -> None:
    """Setup the app to be used for starting an embedded worker."""
    app.finalize()
    app.set_current()
    app.set_default()
    type(app.log)._setup = False
    app.log.setup(loglevel=loglevel, logfile=logfile)
