from anthill.framework.utils.asynchronous import as_future, thread_pool_exec as future_exec
from anthill.framework.core.exceptions import ImproperlyConfigured
from anthill.framework.core.paginator import Paginator, InvalidPage
from anthill.framework.handlers.base import RequestHandler
from anthill.framework.http.errors import Http404
from anthill.framework.utils.translation import translate as _
from anthill.platform.api.rest.handlers.base import SerializableMixin
from sqlalchemy_utils import sort_query
from sqlalchemy.orm import Query
from .base import RestAPIMixin


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

    def get_queryset(self):
        """
        Return the list of items for this handler.

        The return value must be an instance of `sqlalchemy.orm.Query`.
        """
        if isinstance(self.queryset, Query):
            queryset = self.queryset
        elif self.model is not None:
            queryset = self.model.query
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a queryset. Define "
                "%(cls)s.model, %(cls)s.queryset, or override "
                "%(cls)s.get_queryset()." % {
                    'cls': self.__class__.__name__
                }
            )
        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = sort_query(queryset, *ordering)

        return queryset

    def get_ordering(self):
        """Return the field or fields to use for ordering the queryset."""
        return self.ordering

    def paginate_queryset(self, queryset, page_size):
        """Paginate the queryset, if needed."""

        paginator = self.get_paginator(
            queryset, page_size, orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty())
        page_kwarg = self.page_kwarg
        page = self.path_kwargs.get(page_kwarg) or self.get_argument(page_kwarg, 1)
        try:
            page_number = int(page)
        except ValueError:
            if page == 'last':
                page_number = paginator.num_pages
            else:
                raise Http404(_("Page is not 'last', nor can it be converted to an int."))
        try:
            page = paginator.page(page_number)
            return paginator, page, page.object_list, page.has_other_pages()
        except InvalidPage as e:
            raise Http404(_('Invalid page (%(page_number)s): %(message)s') % {
                'page_number': page_number,
                'message': str(e)
            })

    def get_paginate_by(self, queryset):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        return self.paginate_by

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True):
        """Return an instance of the paginator for this handler."""
        return self.paginator_class(
            queryset, per_page, orphans=orphans,
            allow_empty_first_page=allow_empty_first_page)

    def get_paginate_orphans(self):
        """
        Return the maximum number of orphans extend the last page by when
        paginating.
        """
        return self.paginate_orphans

    def get_allow_empty(self):
        """
        Return ``True`` if the handler should display empty lists and ``False``
        if a 404 should be raised instead.
        """
        return self.allow_empty

    def get_context_object_name(self, object_list):
        """Get the name of the item to be used in the context."""
        if self.context_object_name:
            return self.context_object_name
        else:
            return 'object_list'

    async def get_context_data(self, *, object_list=None, **kwargs):
        queryset = object_list if object_list is not None else self.object_list
        if isinstance(queryset, Query):
            queryset = await future_exec(queryset.all)

        page_size = self.get_paginate_by(queryset)
        context_object_name = self.get_context_object_name(queryset)
        context = {
            'is_paginated': False,
        }
        if page_size:
            paginator, page, queryset, is_paginated = self.paginate_queryset(queryset, page_size)
            context['is_paginated'] = is_paginated

        context[context_object_name] = self.serialize(queryset, many=True)
        context.update(kwargs)
        return await super().get_context_data(**context)


class SerializableMultipleObjectsMixin(SerializableMixin):
    pass


class ListMixin(MultipleObjectMixin, SerializableMultipleObjectsMixin, RestAPIMixin):
    async def get(self, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()

        if not allow_empty:
            # When pagination is enabled and object_list is a queryset,
            # it's better to do a cheap query than to load the unpaginated
            # queryset in memory.
            if self.get_paginate_by(self.object_list) is not None:
                is_empty = not (await future_exec(self.object_list.exists))
            else:
                is_empty = not self.object_list
            if is_empty:
                raise Http404(_("Empty list and '%(class_name)s.allow_empty' is False.") % {
                    'class_name': self.__class__.__name__,
                })

        data = await self.get_context_data()
        self.write_json(data=data)


class ListHandler(ListMixin, RequestHandler):
    """A handler for displaying a list of objects."""
