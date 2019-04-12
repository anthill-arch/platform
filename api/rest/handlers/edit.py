from anthill.framework.handlers.base import RequestHandler
from anthill.framework.handlers.detail import SingleObjectMixin, DetailHandler
from anthill.framework.utils.asynchronous import thread_pool_exec
from anthill.framework.forms.orm import model_form
from anthill.framework.db import db


class FormMixin:
    """Provide a way to show and handle a form in a request."""

    initial = {}
    form_class = None
    prefix = None

    def get_initial(self):
        """Return the initial data to use for forms on this handler."""
        return self.initial.copy()

    def get_prefix(self):
        """Return the prefix to use for forms."""
        return self.prefix or ''

    def get_form_class(self):
        """Return the form class to use."""
        return self.form_class

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this handler."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = {
            'data': self.get_initial(),
            'prefix': self.get_prefix(),
        }

        if self.request.method in ('POST', 'PUT'):
            kwargs.update(formdata=dict(self.request.arguments, **self.request.files))
        return kwargs

    async def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""

    async def form_invalid(self, form):
        """If the form is invalid, render the invalid form."""


class ModelFormMixin(FormMixin, SingleObjectMixin):
    """Provide a way to show and handle a ModelForm in a request."""

    def get_model(self):
        if self.model is not None:
            # If a model has been explicitly provided, use it
            return self.model
        elif getattr(self, 'object', None) is not None:
            # If this handler is operating on a single object,
            # use the class of that object
            return self.object.__class__
        else:
            # Try to get a queryset and extract the model class
            # from that
            queryset = self.get_queryset()
            return queryset.one().__class__

    def get_form_class(self):
        """Return the form class to use in this handler."""
        if self.form_class:
            return self.form_class
        else:
            return model_form(self.get_model(), db_session=db.session)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        if hasattr(self, 'object'):
            kwargs.update({'obj': self.object})
        return kwargs

    async def form_valid(self, form):
        """If the form is valid, save the associated model."""
        if self.object is None:
            model = self.get_model()
            # noinspection PyAttributeOutsideInit
            self.object = model()
        form.populate_obj(self.object)
        await thread_pool_exec(self.object.save)
        await super().form_valid(form)


class CreateModelFormMixin(ModelFormMixin):
    pass


class UpdateModelFormMixin(ModelFormMixin):
    def get_form_class(self):
        """Return the form class to use in this handler."""
        form_class = super().get_form_class()
        setattr(form_class.Meta, 'all_fields_optional', True)
        setattr(form_class.Meta, 'assign_required', False)
        return form_class


class ProcessFormHandler(RequestHandler):
    """Processes form on POST or PUT."""

    async def post(self, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = self.get_form()
        if form.validate():
            await self.form_valid(form)
        else:
            await self.form_invalid(form)

    # PUT is a valid HTTP verb for creating (with a known URL) or editing an
    # object, note that browsers only support POST for now.
    async def put(self, *args, **kwargs):
        await self.post(*args, **kwargs)


class FormHandler(FormMixin, ProcessFormHandler):
    """Handler for displaying a form."""


class ModelFormHandler(ModelFormMixin, ProcessFormHandler):
    """Handler for displaying a single object form."""


class CreatingMixin:
    """Provide the ability to create objects."""

    async def post(self, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.object = None
        await super().post(*args, **kwargs)


class CreateHandler(CreatingMixin, ProcessFormHandler):
    """Handler for creating a new object instance."""


class UpdatingMixin:
    """Provide the ability to update objects."""

    async def put(self, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.object = await self.get_object()
        await super().post(*args, **kwargs)


class UpdateHandler(UpdatingMixin, ProcessFormHandler):
    """Handler for updating an existing object."""


class DeletionMixin:
    """Provide the ability to delete objects."""

    async def delete(self, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.object = await self.get_object()
        await thread_pool_exec(self.object.delete)


class DeleteHandler(DeletionMixin, DetailHandler):
    """Handler for deleting an object."""
