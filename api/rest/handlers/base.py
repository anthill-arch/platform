from anthill.framework.handlers import JSONHandler, JSONHandlerMixin
from anthill.framework.core.exceptions import ImproperlyConfigured


class RestAPIMixin(JSONHandlerMixin):
    pass


class SerializableMixin:
    serializer_class = None

    def get_serializer_class(self):
        return self.serializer_class

    def get_serializer(self, many=False):
        serializer_class = self.get_serializer_class()
        if serializer_class is not None:
            return serializer_class(many=many)
        raise ImproperlyConfigured(
            "SerializableMixin requires either a definition of "
            "'serializer_class' or an implementation of 'get_serializer()'")

    def serialize(self, object_list, many=False):
        return self.get_serializer(many).dump(object_list).data
