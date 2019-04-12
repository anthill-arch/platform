from anthill.framework.handlers import WebSocketHandler, JSONRPCMixin
from anthill.platform.core.messenger.channels.handlers.base import ChannelHandlerMixin
from anthill.platform.core.messenger.channels.exceptions import InvalidChannelLayerError
from anthill.platform.core.messenger.channels.layers import get_channel_layer
from anthill.framework.core.jsonrpc.dispatcher import Dispatcher
from tornado.ioloop import IOLoop
import functools


class WebSocketChannelHandler(ChannelHandlerMixin, WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.channel_layer = None
        self.channel_name = None
        self.channel_receive = None

    async def open(self, *args, **kwargs):
        """Invoked when a new WebSocket is opened."""
        await super().open(*args, **kwargs)
        IOLoop.current().add_callback(self.channel_receive_callback)
        # Initialize channel layer
        self.channel_layer = get_channel_layer()
        if self.channel_layer is not None:
            self.channel_name = await self.channel_layer.new_channel()
            self.channel_receive = functools.partial(self.channel_layer.receive, self.channel_name)
        # Add channel groups
        groups = await self.get_groups() or []
        try:
            for group in groups:
                await self.group_add(group)
        except AttributeError:
            raise InvalidChannelLayerError("BACKEND is not configured or doesn't support groups")

    async def send(self, message, binary=False, close=None, reason=None):
        """
        Sends the given message to the client of this Web Socket.
        """
        self.write_message(message, binary=binary)
        if close is not None:
            await self.close(close, reason)

    async def on_connection_close(self):
        # Remove channel groups
        try:
            for group in self.groups:
                await self.group_discard(group)
        except AttributeError:
            raise InvalidChannelLayerError("BACKEND is not configured or doesn't support groups")
        super().on_connection_close()

    def on_close(self):
        """Invoked when the WebSocket is closed."""


class JSONRPCWebSocketChannelHandler(ChannelHandlerMixin, JSONRPCMixin, WebSocketHandler):
    def __init__(self, application, request, dispatcher=None, **kwargs):
        self.dispatcher = dispatcher if dispatcher is not None else Dispatcher()
        super().__init__(application, request, **kwargs)

    def json_rpc_map(self):
        pass
