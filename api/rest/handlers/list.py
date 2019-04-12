from anthill.platform.api.rest.handlers.base import MarshmallowMixin
from anthill.framework.handlers.base import RequestHandler
from anthill.framework.core.paginator import Paginator


class MultipleObjectMixin:
    """A mixin for handlers manipulating multiple objects."""
    allow_empty = True
    queryset = None
    model = None
    paginate_by = None
    paginate_orphans = 0
    context_object_name = None
    paginator_class = Paginator
    page_kwarg = 'page'
    ordering = None


class MarshmallowMultipleObjectsMixin(MarshmallowMixin):
    def get_schema(self):
        schema_class = self.get_schema_class()
        return schema_class(many=True)

    def get_schema_class(self):
        if self.schema_class is None:
            # TODO
            pass
        return super().get_schema_class()


class ListMixin(MultipleObjectMixin, MarshmallowMultipleObjectsMixin):
    pass


class ListHandler(ListMixin, RequestHandler):
    """A handler for displaying a list of objects."""
