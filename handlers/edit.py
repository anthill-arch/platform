from anthill.framework.core.exceptions import ImproperlyConfigured
from anthill.framework.handlers.edit import FormMixin, ProcessFormMixin
from anthill.platform.core.models import RemoteModel


class RemoteModelFormMixin(FormMixin):
    """Provide a way to show and handle a RemoteModelForm in a request."""

    def get_remote_model(self):
        if self.remote_model is not None:
            # If a remote_model has been explicitly provided, use it
            return self.remote_model
        elif getattr(self, 'object', None) is not None:
            # If this handler is operating on a single object,
            # use the class of that object
            return self.object.__class__

    def get_form_class(self):
        """Return the form class to use in this handler."""
        return self.form_class

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        if hasattr(self, 'object'):
            kwargs.update({'obj': self.object})
        return kwargs

    def get_success_url(self):
        """Return the URL to redirect to after processing a valid form."""
        if self.success_url:
            url = self.success_url.format(**self.object.__dict__)
        else:
            try:
                url = self.object.get_absolute_url()
            except AttributeError:
                raise ImproperlyConfigured(
                    "No URL to redirect to. Either provide an url or define "
                    "a get_absolute_url method on the RemoteModel.")
        return url

    async def _form_valid(self, form, force_insert=True):
        """If the form is valid, save the associated model."""
        if self.object is None:
            remote_model = self.get_remote_model()
            # noinspection PyAttributeOutsideInit
            self.object = remote_model()
        form.populate_obj(self.object)
        await self.object.save(force_insert)
        await super().form_valid(form)

    async def form_valid(self, form):
        """If the form is valid, save the associated model."""
        await self._form_valid(form, force_insert=True)


class CreateRemoteModelFormMixin(RemoteModelFormMixin):
    pass


class UpdateRemoteModelFormMixin(RemoteModelFormMixin):
    async def form_valid(self, form):
        """If the form is valid, save the associated model."""
        await super()._form_valid(form, force_insert=False)

