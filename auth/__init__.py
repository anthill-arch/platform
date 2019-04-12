from anthill.framework.core.mail.asynchronous import send_mail
from anthill.platform.core.messenger.message import send_message
from anthill.platform.core.messenger.settings import messenger_settings
from anthill.platform.remote_models import RemoteModel
from anthill.platform.api.internal import RequestError, connector
from tornado.escape import json_decode, json_encode
from functools import partial
from datetime import datetime
import dateutil.parser
import logging

logger = logging.getLogger('anthill.application')


def iso_parse(s):
    return dateutil.parser.parse(s) if isinstance(s, str) else s


class RemoteUser(RemoteModel):
    """
    User model is stored on dedicated service named `login`.
    So, when we deal with user request to some service,
    we need to get user info from remote service to use it locally.
    That's why the RemoteUser need.
    """
    USERNAME_FIELD = 'username'
    IDENTIFIER_FIELD = USERNAME_FIELD
    model_name = 'login.User'

    def __str__(self):
        return self.get_username()

    def __repr__(self):
        return '<RemoteUser(name=%r)>' % self.get_username()

    @property
    def username(self):
        return self._data['username']

    @username.setter
    def username(self, value):
        self._data['username'] = value

    @property
    def email(self):
        return self._data['email']

    @email.setter
    def email(self, value):
        self._data['email'] = value

    @property
    def created(self) -> datetime:
        return iso_parse(self._data.get('created', None))

    @property
    def last_login(self) -> datetime:
        return iso_parse(self._data.get('last_login', None))

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_username(self):
        """Return the identifying username for this RemoteUser."""
        return getattr(self, self.USERNAME_FIELD)

    # async def save(self, force_insert=False):
    #    raise NotImplementedError("Service doesn't provide a DB representation for RemoteUser.")

    # async def delete(self):
    #    raise NotImplementedError("Service doesn't provide a DB representation for RemoteUser.")

    def set_password(self, raw_password):
        raise NotImplementedError("Service doesn't provide a DB representation for RemoteUser.")

    def check_password(self, raw_password):
        raise NotImplementedError("Service doesn't provide a DB representation for RemoteUser.")

    async def get_profile(self) -> "RemoteProfile":
        data = await self.internal_request('profile', 'get_profile', user_id=self.user_id)
        return RemoteProfile(**data)

    async def send_mail(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        await send_mail(subject, message, from_email, [self.email], **kwargs)

    @staticmethod
    async def send_message_by_user_id(user_id, message, callback=None, client=None, content_type=None):
        create_personal_group = messenger_settings.PERSONAL_GROUP_FUNCTION
        data = {
            'data': message,
            'group': create_personal_group(user_id),
            'content_type': content_type,
            'trusted': True,
        }
        await send_message(
            event='create_message',
            data=data,
            callback=callback,
            client=client
        )

    async def send_message(self, message, callback=None, client=None, content_type=None):
        """Send a message to this user."""
        await self.send_message_by_user_id(self.id, message, callback, client, content_type)


class RemoteProfile(RemoteModel):
    """
    Profile model is stored on dedicated service named `profile`.
    So, when we deal with user request to some service,
    we need to get user profile info from remote service to use it locally.
    That's why the RemoteProfile need.
    """
    model_name = 'profile.Profile'

    def __repr__(self):
        return '<RemoteProfile(user_id=%r)>' % self.user_id

    async def get_user(self) -> RemoteUser:
        data = await self.internal_request('login', 'get_user', user_id=self.user_id)
        return RemoteUser(**data)

    @property
    def user_id(self):
        return self._data['user_id']

    @property
    def payload(self) -> dict:
        return json_decode(self._data.get('payload', '{}'))

    @payload.setter
    def payload(self, value: dict):
        self._data['payload'] = json_encode(value)

    @property
    def created(self) -> datetime:
        return iso_parse(self._data.get('created', None))

    @property
    def updated(self) -> datetime:
        return iso_parse(self._data.get('updated', None))


async def internal_authenticate(internal_request=None, **credentials) -> RemoteUser:
    """Perform internal api authentication."""
    internal_request = internal_request or connector.internal_request
    do_authenticate = partial(internal_request, 'login', 'authenticate')
    try:
        data = await do_authenticate(credentials=credentials)  # User data dict
    except RequestError as e:
        logger.error(str(e))
    else:
        return RemoteUser(**data)
