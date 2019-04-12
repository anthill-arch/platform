from anthill.framework.conf import settings
from importlib import import_module
import six


USER_SETTINGS = getattr(settings, 'MESSENGER', None)


DEFAULTS = {
    'PERSONAL_GROUP_PREFIX': '__user',  # Must starts with `__` for security reason
    'PERSONAL_GROUP_FUNCTION': 'anthill.platform.core.messenger.client.backends.base.create_personal_group',
    'MODERATORS': [
        {
            'NAME': 'anthill.platform.core.messenger.moderators.MaximumMessageLengthModerator',
            'OPTIONS': {
                'max_length': 512,
            }
        },
    ]
}

IMPORT_STRINGS = (
    'PERSONAL_GROUP_FUNCTION',
)


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if val is None:
        return None
    elif isinstance(val, six.string_types):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        # Nod to tastypie's use of importlib.
        module_path, class_name = val.rsplit('.', 1)
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        msg = "Could not import '%s' for MESSENGER setting '%s'. " \
              "%s: %s." % (val, setting_name, e.__class__.__name__, e)
        raise ImportError(msg)


class MessengerSettings:
    """
    A settings object, that allows messenger settings to be accessed as properties.

    For example:
        from anthill.framework.platform.core.messenger.settings import messenger_settings
        print(messenger_settings.PERSONAL_GROUP_PREFIX)

    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.
    """
    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        self._user_settings = user_settings
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        if not hasattr(self, '_user_settings'):
            self._user_settings = getattr(settings, 'MESSENGER', {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError("Invalid messenger setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = perform_import(val, attr)

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, '_user_settings'):
            delattr(self, '_user_settings')


messenger_settings = MessengerSettings(USER_SETTINGS, DEFAULTS, IMPORT_STRINGS)
