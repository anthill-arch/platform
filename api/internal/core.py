from tornado.gen import with_timeout
from tornado.util import TimeoutError
from tornado.ioloop import IOLoop
from tornado.concurrent import Future
from tornado.escape import utf8

from anthill.framework.testing.timing import ElapsedTime
from anthill.framework.utils.singleton import Singleton
from anthill.platform.core.messenger.channels.layers import get_channel_layer
from anthill.platform.core.messenger.channels.exceptions import InvalidChannelLayerError
from functools import wraps, partial
import datetime

from anthill.framework.core.jsonrpc.exceptions import JSONRPCInvalidRequestException
from anthill.framework.core.jsonrpc.jsonrpc import JSONRPCRequest
from anthill.framework.core.jsonrpc.manager import JSONRPCResponseManager
from anthill.framework.core.jsonrpc.dispatcher import Dispatcher
from anthill.framework.utils.asynchronous import as_future
from anthill.framework.core.cache import cache
from anthill.framework.conf import settings

from typing import Optional
import inspect
import json
import logging
import hashlib
import copy

__all__ = [
    'BaseInternalConnection', 'InternalConnection', 'JSONRPCInternalConnection',
    'as_internal', 'api', 'InternalAPI', 'InternalAPIMixin', 'InternalAPIConnector',
    'InternalAPIError', 'RequestTimeoutError', 'RequestError', 'connector',
    'ServiceDoesNotExist'
]

logger = logging.getLogger('anthill.application')


DEFAULT_CACHE_TIMEOUT = getattr(settings, 'INTERNAL_DEFAULT_CACHE_TIMEOUT', 300)
INTERNAL_REQUEST_CACHING = getattr(settings, 'INTERNAL_REQUEST_CACHING', True)
INTERNAL_API_METHOD_CACHING = getattr(settings, 'INTERNAL_API_METHOD_CACHING', False)


def cache_key(service, method, postfix=None):
    parts = ['internal.cache', service, method]
    if postfix:
        parts.append(postfix)
    return '.'.join(parts)


def _cached(key, timeout):
    def decorator(func):
        @wraps(func)
        async def wrapper(conn, service, method, *args, **kwargs):
            caching = kwargs.pop('caching', INTERNAL_REQUEST_CACHING)
            if not caching:
                return await func(conn, service, method, *args, **kwargs)
            timeout_ = kwargs.pop('cache_timeout', timeout)
            postfix = hashlib.md5(utf8(str(args) + str(kwargs))).hexdigest()
            k = key(service, method, postfix) if callable(key) else key
            result = await as_future(cache.get)(k)
            if result is None:
                result = await func(conn, service, method, *args, **kwargs)
                await as_future(cache.set)(k, result, timeout_)
            return result
        return wrapper
    return decorator


cached = _cached(key=cache_key, timeout=DEFAULT_CACHE_TIMEOUT)


class InternalAPIError(Exception):
    """General internal API error."""


class RequestError(InternalAPIError):
    pass


class RequestTimeoutError(RequestError):
    pass


class ServiceDoesNotExist(Exception):
    pass


class InternalAPI(Singleton):
    """Internal API methods."""

    methods = []

    def __init__(self):
        self.service = None

    def __iter__(self):
        return iter(self.methods)

    def __getitem__(self, key):
        return self.methods[key]

    def __repr__(self):
        return repr(self.methods)

    def __len__(self):
        return len(self.methods)

    def add_method(self, method):
        self.methods.append(method.__name__)
        setattr(self.__class__, method.__name__, method)

    def add_methods(self, methods):
        for method in methods:
            self.add_method(method)

    def as_internal(self, enable_cache=INTERNAL_API_METHOD_CACHING,
                    cache_timeout=DEFAULT_CACHE_TIMEOUT, cache_key=cache_key):
        """Decorator marks function as an internal api method."""

        def decorator(func):
            def get_cache_key(api_, *args, **kwargs):
                kwargs = copy.deepcopy(kwargs)
                del kwargs['service']
                method = func.__name__
                postfix = hashlib.md5(utf8(str(args) + str(kwargs))).hexdigest()
                key = cache_key(self.service.name, method, postfix) if callable(cache_key) else cache_key
                return key

            if inspect.iscoroutinefunction(func):
                async def wrapper(api_, *args, **kwargs):
                    key = None
                    if enable_cache:
                        key = get_cache_key(api_, *args, **kwargs)
                        result = await as_future(cache.get)(key)
                        if result:
                            return result
                    try:
                        result = await func(api_, *args, **kwargs)
                    except Exception as e:
                        return {'error': {'message': str(e)}}
                    else:
                        if enable_cache:
                            await as_future(cache.set)(key, result, cache_timeout)
                        return result
            else:
                def wrapper(api_, *args, **kwargs):
                    if enable_cache:
                        logger.warning('Caching cannot be enabled. Make api method async.')
                    try:
                        result = func(api_, *args, **kwargs)
                    except Exception as e:
                        return {'error': {'message': str(e)}}
                    else:
                        return result
            wrapper = wraps(func)(wrapper)
            self.add_method(wrapper)
            return wrapper

        return decorator


api = InternalAPI()
as_internal = api.as_internal


class BaseInternalConnection(Singleton):
    """Implements communications between services."""
    message_type = 'internal'
    channel_alias = 'internal'
    channel_group_name_prefix = 'internal'
    request_timeout = 10

    def __init__(self, service=None):
        self.channel_layer = None
        self.channel_name = None
        self.channel_receive = None
        self.service = service
        self._responses = {}
        self._current_request_id = 0
        super().__init__()

    def channel_group_name(self, service=None) -> str:
        service_name = service or self.service.name
        return '_'.join([self.channel_group_name_prefix, service_name])

    async def channel_receive_callback(self) -> None:
        """Messages listener callback."""
        if self.channel_receive:
            while True:
                message = await self.channel_receive()
                if not message.get('type', None):
                    raise ValueError('Worker received message with no type.')
                await self.on_message(message)

    async def connect(self) -> None:
        IOLoop.current().add_callback(self.channel_receive_callback)
        self.channel_layer = get_channel_layer(alias=self.channel_alias)
        if self.channel_layer is not None:
            self.channel_name = await self.channel_layer.new_channel(prefix=self.service.app.label)
            self.channel_receive = partial(self.channel_layer.receive, self.channel_name)
            await self.channel_layer.group_add(self.channel_group_name(), self.channel_name)
            logger.debug('Internal api connection status: CONNECTED.')
        else:
            logger.debug('Internal api connection status: NOT_CONNECTED.')

    async def disconnect(self) -> None:
        await self.channel_layer.group_discard(
            self.channel_group_name(), self.channel_name)
        logger.debug('Internal api connection status: DISCONNECTED.')

    async def group_send(self, service: str, message: dict) -> None:
        """Send message to service channel group."""
        try:
            await self.channel_layer.group_send(self.channel_group_name(service), message)
        except AttributeError:
            raise InvalidChannelLayerError(
                "BACKEND is not configured or doesn't support groups")

    async def send(self, channel: str, message: dict) -> None:
        """Send message to service channel."""
        await self.channel_layer.send(channel, message)

    def next_request_id(self):
        """Generate new request id."""
        self._current_request_id += 1
        return self._current_request_id

    async def on_request(self, payload: dict, channel: str) -> None:
        raise NotImplementedError

    async def on_result(self, payload: dict) -> None:
        raise NotImplementedError

    async def on_error(self, payload: dict) -> None:
        raise NotImplementedError

    async def on_message(self, message: dict) -> None:
        raise NotImplementedError

    async def request(self, service: str, method: str, timeout: int = None, **kwargs) -> dict:
        """Request for method and wait for result."""
        raise NotImplementedError

    async def push(self, service: str, method: str, **kwargs) -> None:
        """Request for method with no wait for result."""
        raise NotImplementedError


class JSONRPCInternalConnection(BaseInternalConnection):
    message_type = 'internal_json_rpc'
    json_rpc_ver = '2.0'  # Only 2.0 supported!

    def __init__(self, service=None, dispatcher=None):
        super().__init__(service)
        self.dispatcher = dispatcher if dispatcher is not None else Dispatcher()
        for method_name in api:
            self.dispatcher.add_method(getattr(api, method_name))

    async def on_request(self, payload: dict, channel: str) -> None:
        payload = json.dumps(payload)
        try:
            json_rpc_request = JSONRPCRequest.from_json(payload)
        except (TypeError, ValueError, JSONRPCInvalidRequestException):
            response = await JSONRPCResponseManager.handle(payload, self.dispatcher)
        else:
            json_rpc_request.params = json_rpc_request.params or {}
            response = await JSONRPCResponseManager.handle_request(
                json_rpc_request, self.dispatcher)

        # No reply needed if response is None (in case of push).
        if response is None:
            return

        msg = {
            'type': self.message_type,
            'service': self.service.name,
            'payload': response.data
        }

        await self.send(channel, msg)  # send response

    async def on_result(self, payload: dict) -> None:
        request_id = payload.get('id')
        try:
            future = self._responses[request_id]
        except KeyError:
            pass  # ¯\_(ツ)_/¯
        else:
            result = payload['result']
            future.set_result(result)

    async def on_error(self, payload: dict) -> None:
        request_id = payload.get('id')
        try:
            future = self._responses[request_id]
        except KeyError:
            pass  # ¯\_(ツ)_/¯
        else:
            del payload['error']['code']
            error = dict(error=payload['error'])
            future.set_result(error)

    async def on_message(self, message: dict) -> None:
        payload = message['payload']
        if 'result' in payload:
            await self.on_result(payload)
        elif 'error' in payload:
            await self.on_error(payload)
        elif 'method' in payload:
            await self.on_request(payload, channel=message['channel'])
        else:
            raise ValueError('Invalid message: %s' % message)

    @staticmethod
    def _is_response_valid(response: Optional[dict]) -> bool:
        if isinstance(response, dict) and 'error' in response:
            return False
        return True

    # noinspection PyMethodMayBeStatic
    def check_service(self, service, registered_services=None):
        if callable(registered_services):
            registered_services = registered_services()
        if registered_services is not None and service not in registered_services:
            raise ServiceDoesNotExist

    @cached
    async def request(self, service: str, method: str, timeout: int = None, registered_services=None,
                      **kwargs) -> dict:
        self.check_service(service, registered_services)
        with ElapsedTime('request@InternalConnection -> {0}@{1}', method, service):
            kwargs.update(service=self.service.name)
            request_id = self.next_request_id()
            message = {
                'type': self.message_type,
                'service': self.service.name,
                'channel': self.channel_name,
                'payload': {
                    'jsonrpc': self.json_rpc_ver,
                    'method': method,
                    'params': kwargs,
                    'id': request_id
                }
            }
            self._responses[request_id] = future = Future()
            await self.group_send(service, message)
            timeout = timeout or self.request_timeout
            try:
                result = await with_timeout(datetime.timedelta(seconds=timeout), future)
            except TimeoutError:
                raise RequestTimeoutError(
                    'Service `%s` not responded for %s sec' % (service, timeout))
                # return {'error': {'message': 'Service `%s` not responded for %s sec' % (service, timeout)}}
            else:
                if not self._is_response_valid(result):
                    raise RequestError(result)
                return result
            finally:
                del self._responses[request_id]

    async def push(self, service: str, method: str, registered_services=None, **kwargs) -> None:
        self.check_service(service, registered_services)
        with ElapsedTime('push@InternalConnection -> {0}@{1}', method, service):
            kwargs.update(service=self.service.name)
            message = {
                'type': self.message_type,
                'service': self.service.name,
                'payload': {
                    'jsonrpc': self.json_rpc_ver,
                    'method': method,
                    'params': kwargs
                }
            }
            await self.group_send(service, message)


InternalConnection = JSONRPCInternalConnection  # More simple alias


class InternalAPIMixin:
    """Includes internal api operations."""
    internal_connection_class = InternalConnection

    @property
    def internal_connection(self):
        return self.internal_connection_class()

    @property
    def internal_request(self):
        return self.internal_connection.request

    @property
    def internal_push(self):
        return self.internal_connection.push


class InternalAPIConnector(InternalAPIMixin):
    pass


connector = InternalAPIConnector()
