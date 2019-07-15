from anthill.framework.handlers import RequestHandler
from anthill.framework.utils.asynchronous import thread_pool_exec as future_exec, as_future
from anthill.framework.core.exceptions import ImproperlyConfigured
from anthill.framework.http import Http404
from anthill.platform.api.rest.handlers.base import SerializableMixin
from .base import RestAPIMixin


class SingleObjectMixin:
    """
    Provide the ability to retrieve a single object for further manipulation.
    """
    model = None
    queryset = None
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    pk_url_kwarg = 'id'
    query_pk_and_slug = False

    @as_future
    def get_object(self, queryset=None):
        """
        Return the object the handler is displaying.

        Require `self.queryset` and a `id` or `slug` argument in the url entry.
        Subclasses can override this to return any object.
        """
        # Use a custom queryset if provided.
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.path_kwargs.get(self.pk_url_kwarg)
        slug = self.path_kwargs.get(self.slug_url_kwarg)
        if pk is not None:
            queryset = queryset.filter_by(id=pk)

        # Next, try looking up by slug.
        if slug is not None and (pk is None or self.query_pk_and_slug):
            slug_field = self.get_slug_field()
            queryset = queryset.filter_by(**{slug_field: slug})

        # If none of those are defined, it's an error.
        if pk is None and slug is None:
            raise AttributeError(
                "Generic detail handler %s must be called with either an object "
                "pk or a slug in the url." % self.__class__.__name__)

        # Get the single item from the filtered queryset
        obj = queryset.one_or_none()
        if obj is None:
            raise Http404

        return obj

    def get_queryset(self):
        """
        Return the queryset that will be used to look up the object.

        This method is called by the default implementation of get_object() and
        may not be called if get_object() is overridden.
        """
        if self.queryset is None:
            if self.model:
                return self.model.query
            else:
                raise ImproperlyConfigured(
                    "%(cls)s is missing a queryset. Define "
                    "%(cls)s.model, %(cls)s.queryset, or override "
                    "%(cls)s.get_queryset()." % {
                        'cls': self.__class__.__name__
                    }
                )
        return self.queryset

    def get_slug_field(self):
        """Get the name of a slug field to be used to look up by slug."""
        return self.slug_field


class SerializableSingleObjectMixin(SerializableMixin):
    def get_serializer_class(self):
        if self.serializer_class is None:
            try:
                return self.object.__marshmallow__
            except AttributeError:
                raise ImproperlyConfigured(
                    "No serializer class for dumping data. Either provide a serializer_class "
                    "or define schema on the Model.")
        return super().get_serializer_class()


class DetailMixin(SingleObjectMixin, SerializableSingleObjectMixin, RestAPIMixin):
    async def get(self, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.object = await self.get_object()
        self.write_json(data=self.serialize(self.object))


class DetailHandler(DetailMixin, RequestHandler):
    pass
