from anthill.framework.core.exceptions import ImproperlyConfigured
from anthill.framework.utils.text import capfirst
from anthill.platform.api.internal import InternalAPIMixin
from typing import Type, Optional


class RemoteModel(InternalAPIMixin):
    """Class for representing model object from remote server."""

    IDENTIFIER_FIELD = 'id'
    model_name = None  # Format: `<service_name>.<model_name>`

    def __init__(self, **kwargs):
        self._data = kwargs

    def __repr__(self):
        return '<RemoteModel(service=%(service)s, model=%(model)s, identifier=%(identifier)s)>' % {
            'service': self.get_service_name(),
            'model': self.get_model_name(),
            'identifier': self.get_identifier()
        }

    def __getattr__(self, item):
        return self._data[item]

    def _parse_model_name(self):
        return self.model_name.split('.')

    def get_service_name(self):
        return self._parse_model_name()[0]

    def get_model_name(self):
        return self._parse_model_name()[1]

    def get_identifier(self):
        """Return the identifying field for this RemoteModelMixin."""
        return getattr(self, self.IDENTIFIER_FIELD)

    async def request(self, action, **kwargs):
        return await self.internal_request(self.get_service_name(), action, **kwargs)

    def to_dict(self):
        return self._data.copy()

    async def get(self):
        """Perform get model operation on remote server."""
        kwargs = await self.request(
            'get_model',
            model_name=self.get_model_name(),
            object_id=self.get_identifier(),
            identifier_name=self.IDENTIFIER_FIELD
        )
        self._data.update(kwargs)
        return self

    async def delete(self):
        """Perform delete model operation on remote server."""
        await self.request(
            'delete_model',
            model_name=self.get_model_name(),
            object_id=self.get_identifier(),
            identifier_name=self.IDENTIFIER_FIELD
        )

    async def save(self):
        """Perform save model operation on remote server."""
        kwargs = await self.request(
            'update_or_create_model',
            model_name=self.get_model_name(),
            **self._data
        )
        self._data.update(kwargs)
        return self

    # def get_absolute_url(self):
    #    pass


def remote_model_factory(path: str, name: Optional[str] = None) -> Type[RemoteModel]:
    """Generate a model class based on RemoteModel.

    :param path: path to the target model
    :param name: name of generated model
    """
    service_name, model_name = path.split('.')

    def remote_model_name():
        if name:
            return name
        if model_name == capfirst(service_name):
            return 'Remote' + model_name
        return 'Remote' + capfirst(service_name) + model_name

    class Model(RemoteModel):
        def __repr__(self):
            return '<%(remote_model_name)s(%(identifier_name)s=%(identifier_value)s)>' % {
                'identifier_name': self.IDENTIFIER_FIELD,
                'identifier_value': self.get_identifier(),
                'remote_model_name': remote_model_name()
            }

    Model.model_name = model_path
    Model.__name__ = remote_model_name()

    return Model
