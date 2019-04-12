from anthill.framework.core.exceptions import ImproperlyConfigured, ValidationError
from anthill.framework.utils.module_loading import import_string
from .settings import messenger_settings
import functools


class ModeratedException(ValidationError):
    pass


@functools.lru_cache(maxsize=None)
def get_default_message_moderators():
    return get_message_moderators(messenger_settings.MODERATORS)


def get_message_moderators(moderator_config):
    moderators = []
    for moderator in moderator_config:
        try:
            klass = import_string(moderator['NAME'])
        except ImportError:
            msg = "The module in NAME could not be imported: %s." \
                  "Check your MODERATORS setting."
            raise ImproperlyConfigured(msg % moderator['NAME'])
        moderators.append(klass(**moderator.get('OPTIONS', {})))
    return moderators


async def moderate_message(message, message_moderators=None):
    """
    Validate whether the message meets all moderator requirements.

    If the message is valid, return ``None``.
    If the message is invalid, raise ModeratedException with all error messages.
    """
    errors = []
    if message_moderators is None:
        message_moderators = get_default_message_moderators()
    for moderator in message_moderators:
        try:
            await moderator.moderate(message)
        except ModeratedException as error:
            errors.append(error)
    if errors:
        raise ModeratedException(errors)


def message_moderators_help_texts(message_moderators=None):
    """
    Return a list of all help texts of all configured moderators.
    """
    help_texts = []
    if message_moderators is None:
        message_moderators = get_default_message_moderators()
    for moderator in message_moderators:
        help_texts.append(moderator.get_help_text())
    return help_texts


class MaximumMessageLengthModerator:
    """
    Validate whether the message contains less than a maximum length.
    """

    def __init__(self, max_length=256):
        self.max_length = max_length

    def get_help_text(self):
        return "Your message must not contain more than %(max_length)d characters." % {'max_length': self.max_length}

    async def moderate(self, message: str) -> None:
        if len(message) > self.max_length:
            raise ModeratedException(
                "This message is too long. It must not contain more than %(max_length)d characters.",
                code='message_too_long',
                params={'max_length': self.max_length},
            )
