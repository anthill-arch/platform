from anthill.framework.handlers import WebSocketJSONRPCHandler
from anthill.platform.handlers.base import InternalRequestHandlerMixin

__all__ = ['JsonRPCSessionHandler', 'jsonrpc_method']


def jsonrpc_method(**kwargs):
    """Marks session handler method as json-rpc method."""

    def decorator(func):
        func.jsonrpc_method = True
        func.kwargs = kwargs
        return func

    return decorator


class JsonRPCSessionHandler(InternalRequestHandlerMixin, WebSocketJSONRPCHandler):
    """
    Json-rpc session channel.

    Example:

        class JsonRPCExampleSessionHandler(JsonRPCSessionHandler):
            @jsonrpc_method(name='alias_name')
            def method_name(self):
                ...
    """

    def __init__(self, application, request, dispatcher=None, **kwargs):
        super().__init__(application, request, dispatcher, **kwargs)
        self._setup_methods()

    def _setup_methods(self):
        for method_name in self.__class__.__dict__:
            attr = getattr(self, method_name)
            if getattr(attr, 'jsonrpc_method', False):
                kwargs = getattr(attr, 'kwargs', {})
                name = kwargs.get('name', method_name)
                self.dispatcher.add_method(attr, name)
