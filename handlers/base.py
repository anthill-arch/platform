from anthill.framework.auth.models import AnonymousUser
from anthill.framework.auth import _get_user_session_key, HASH_SESSION_KEY
from anthill.framework.utils.crypto import constant_time_compare
from anthill.framework.auth.log import get_user_logger, ApplicationLogger
from anthill.platform.auth import RemoteUser


class UserHandlerMixin:
    async def get_user(self):
        """
        Return the user model instance associated with the given session.
        If no user is retrieved, return an instance of `AnonymousUser`.
        """
        user = None
        try:
            user_id = _get_user_session_key(self)
        except KeyError:
            pass
        else:
            user = await RemoteUser(id=user_id).get()
            # Verify the session
            if hasattr(user, 'get_session_auth_hash'):
                session_hash = self.session.get(HASH_SESSION_KEY)
                session_hash_verified = session_hash and constant_time_compare(
                    session_hash,
                    user.get_session_auth_hash()
                )
                if not session_hash_verified:
                    self.session.flush()
                    user = None

        return user or AnonymousUser()

    # noinspection PyAttributeOutsideInit
    async def prepare(self):
        # super().prepare()
        self.current_user = await self.get_user()
        self.user_logger = get_user_logger(self.current_user)
        self.app_logger = ApplicationLogger(self.current_user)
        try:
            self.messenger_client = self.application.create_messenger_client()
        except KeyError:
            self.messenger_client = None


class InternalRequestHandlerMixin:
    @property
    def internal_request(self):
        """
        An alias for `self.application.internal_connection.request
        <InternalConnection.request>`.
        """
        return self.application.internal_connection.request
