"""
Rate limit use general caching system.
Usage:
    from anthill.platform.security.rate_limit import default_rate_limit

    @default_rate_limit('ip', ip_address)
    def function_name():
        # function code
        ...


    def exceeded_callback(*args, **kwargs):
        # function code
        ...

    @default_rate_limit('create_room', account_id,
                        exceeded_callback=exceeded_callback, *args, **kwargs)
    def function_name():
        # function code
        ...
"""
from anthill.framework.core.cache import caches
from anthill.framework.conf import settings
from anthill.framework.utils.module_loading import import_string
from anthill.framework.core.exceptions import ImproperlyConfigured
from functools import wraps
import threading
import logging

logger = logging.getLogger('anthill.rate_limit')
cache = caches['rate_limit']

RATE_LIMIT_ENABLE = getattr(settings, 'RATE_LIMIT_ENABLE', False)
RATE_LIMIT_CONFIG = getattr(settings, 'RATE_LIMIT_CONFIG', {})

__all__ = ['RateLimit', 'RateLimitException', 'default_rate_limit']


class RateLimitException(Exception):
    """
    Rate limit exception class.
    """

    def __init__(self, state=None, message=''):
        super(RateLimitException, self).__init__(message)
        self.state = state or {}


class RateLimitConfig(dict):
    _PERIODS = {
        's': 1,  # seconds
        'm': 60,  # minutes
        'h': 60 * 60,  # hours
        'd': 24 * 60 * 60,  # days
        'w': 7 * 24 * 60 * 60  # weeks
    }

    # noinspection PyMethodMayBeStatic
    def _parse_callback(self, entry):
        callback = entry.get('callback')
        if callback is not None:
            try:
                fn = import_string(callback)
                if fn is not None and not callable(fn):
                    raise ImproperlyConfigured('Rate limit callback is not callable')
                return fn
            except ImportError:
                pass

    def _parse_rate(self, entry):
        rate = entry.get('rate')
        requests_num, raw_duration = rate.split('/')
        requests_num = int(requests_num)
        raw_duration = raw_duration.strip()
        duration_num = int(raw_duration[:-1] or 1)
        duration_unit = raw_duration[-1]
        return requests_num, duration_num * self._PERIODS[duration_unit]

    def __call__(self):
        config = {}
        for k, v in self.items():
            config[k] = dict(
                block=v.get('block'),
                callback=self._parse_callback(v),
                rate=self._parse_rate(v)
            )
        return config


class RateLimit:
    config_factory = RateLimitConfig(RATE_LIMIT_CONFIG)

    def __init__(self, storage):
        self.storage = storage
        self.config = self.config_factory()

        # Add thread safety.
        self.lock = threading.RLock()

    def __call__(self, resource_name, resource_key, exceeded_callback=None, *args, **kwargs):
        if exceeded_callback is not None and not callable(exceeded_callback):
            raise ImproperlyConfigured('Exceeded callback is not callable')

        def decorator(func):
            @wraps(func)
            def wrapper(*f_args, **f_kwargs):
                if not RATE_LIMIT_ENABLE or not RATE_LIMIT_CONFIG:
                    if RATE_LIMIT_ENABLE and not RATE_LIMIT_CONFIG:
                        logger.warning('Rate limit is not configured.')
                    return func(*f_args, **f_kwargs)
                if resource_name not in self.config:
                    logger.error('Resource `%s` is not configured.' % resource_name)
                    return

                rate_requests_max, rate_duration_max = self.config[resource_name]['rate']

                storage_key = self.build_storage_key(resource_name, resource_key)

                with self.lock:
                    rate_requests = self.storage.get(storage_key)
                    if rate_requests is None:
                        self.storage.set(storage_key, 1, timeout=rate_duration_max)
                    elif rate_requests < rate_requests_max:
                        self.storage.incr(storage_key)
                    else:
                        block = self.config[resource_name]['block']
                        callback = self.config[resource_name]['callback']
                        state = dict(
                            rate_storage_key=storage_key,
                            rate_requests_max=rate_requests_max,
                            rate_duration=rate_duration_max,
                            rate_requests=rate_requests,
                            rate_resource_name=resource_name,
                            rate_resource_key=resource_key
                        )
                        if block:
                            if exceeded_callback is None:
                                raise RateLimitException(state)
                            else:
                                kwargs.update(state)
                                exceeded_callback(*args, **kwargs)
                                return
                        elif callback is not None:
                            callback(**state)
                    try:
                        return func(*f_args, **f_kwargs)
                    except Exception:
                        # Fallback first then re-raise exception
                        if rate_requests is not None and rate_requests > 0:
                            self.storage.decr(storage_key)
                        raise

            return wrapper

        return decorator

    def reset(self, storage_key):
        """Reset limits by storage key."""
        with self.lock:
            return self.storage.delete(storage_key)

    def reset_all(self):
        """Reset all limits."""
        with self.lock:
            return self.storage.clear()

    def build_storage_key(self, resource_name, resource_key):
        return ':'.join([resource_name, resource_key])


default_rate_limit = RateLimit(storage=cache)
