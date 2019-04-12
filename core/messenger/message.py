from anthill.framework.handlers.socketio import socketio_client
import socketio
import logging

logger = logging.getLogger('anthill.application')


class MessengerClient:
    def __init__(self, url, namespace='/messenger'):
        self.url = url
        self.namespace = namespace or '/'
        self._client = socketio_client
        self.register_namespace()

    class _SocketIOClientNamespace(socketio.AsyncClientNamespace):
        def on_connect(self):
            logger.debug('Client has been connected to messenger.')

        def on_disconnect(self):
            logger.debug('Client has been disconnected from messenger.')

    def __repr__(self):
        return "<%s(url=%r, namespace=%r)>" % (self.__class__.__name__, self.url, self.namespace)

    def register_namespace(self):
        self._client.register_namespace(self._SocketIOClientNamespace(self.namespace))

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.close()

    async def connect(self):
        await self._client.connect(self.url, namespaces=[self.namespace])

    async def emit(self, event, data=None, namespace=None, callback=None):
        await self._client.emit(
            event, data=data, namespace=namespace or self.namespace, callback=callback)
        logger.debug('Message has been sent.')

    def close(self):
        self._client.disconnect()


async def send_message(event, data=None, namespace=None, callback=None, client=None):
    if client is None:
        from anthill.framework.apps import app
        client = app.service.messenger_client
    await client.emit(event, data, namespace, callback)
