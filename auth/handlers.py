from anthill.framework.auth.models import AnonymousUser
from anthill.framework.conf import settings
from anthill.framework.handlers.base import RequestHandler, RedirectHandler, TemplateHandler
from anthill.framework.handlers.edit import FormHandler
from anthill.framework.utils.crypto import constant_time_compare
from anthill.framework.auth import (
    _get_user_session_key,
    HASH_SESSION_KEY,
    REDIRECT_FIELD_NAME,
    SESSION_KEY
)
from anthill.framework.auth.log import get_user_logger, ApplicationLogger
from anthill.platform.auth.forms import AuthenticationForm
from anthill.platform.auth import RemoteUser
from anthill.platform.services import MessengerClient
from wtforms import ValidationError

__all__ = [
    'UserHandlerMixin',
    'LoginHandlerMixin',
    'LogoutHandlerMixin',
    'AuthHandlerMixin',
    'UserRequestHandler',
    'UserTemplateHandler',
    'LoginHandler',
    'LogoutHandler'
]


class InvalidLoginError(Exception):
    pass


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
        await super().prepare()
        self.current_user = await self.get_user()
        self.user_logger = get_user_logger(self.current_user)
        self.app_logger = ApplicationLogger(self.current_user)
        try:
            self.messenger_client = self.application.create_messenger_client()
        except KeyError:
            self.messenger_client = None


class LoginHandlerMixin:
    async def login(self, user: RemoteUser):
        """
        Persist a user id and a backend in the request. This way a user doesn't
        have to reauthenticate on every request. Note that data set during
        the anonymous session is retained when the user logs in.
        """
        session_auth_hash = ''
        if user is None:
            user = self.current_user
        if hasattr(user, 'get_session_auth_hash'):
            session_auth_hash = user.get_session_auth_hash()

        if SESSION_KEY in self.session:
            if _get_user_session_key(self) != user.id or (
                    session_auth_hash and
                    not constant_time_compare(self.session.get(HASH_SESSION_KEY, ''), session_auth_hash)):
                # To avoid reusing another user's session, create a new, empty
                # session if the existing session corresponds to a different
                # authenticated user.
                self.session.flush()
        else:
            self.session.cycle_key()

        self.session[SESSION_KEY] = user.id
        self.session[HASH_SESSION_KEY] = session_auth_hash
        # noinspection PyAttributeOutsideInit
        self.current_user = user


class LogoutHandlerMixin:
    async def logout(self):
        if not isinstance(self.current_user, (AnonymousUser, type(None))):
            self.session.flush()
            # noinspection PyAttributeOutsideInit
            self.current_user = AnonymousUser()


class AuthHandlerMixin(UserHandlerMixin, LoginHandlerMixin, LogoutHandlerMixin):
    pass


class UserRequestHandler(UserHandlerMixin, RequestHandler):
    """User aware RequestHandler."""


class LoginHandler(LoginHandlerMixin, FormHandler):
    """Display the login form and handle the login action."""

    form_class = AuthenticationForm
    authentication_form = None
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'login.html'
    redirect_authenticated_user = False
    extra_context = None

    def get_success_url(self):
        url = self.get_redirect_url()
        return url or self.reverse_url(settings.LOGIN_REDIRECT_URL)

    def get_redirect_url(self):
        """Return the user-originating redirect URL."""
        redirect_to = self.get_argument(
            self.redirect_field_name,
            self.get_query_argument(self.redirect_field_name, '')
        )
        return redirect_to

    def get_form_class(self):
        return self.authentication_form or self.form_class

    async def login_error(self, form):
        context = await self.get_context_data(form=form)
        self.render(**context)

    async def form_valid(self, form):
        """Security check complete. Log the user in."""
        try:
            user = await form.authenticate()
        except ValidationError:
            await self.login_error(form)
        else:
            try:
                await self.login(user=user)
            except InvalidLoginError:
                await self.login_error(form)
            else:
                self.redirect(self.get_success_url())


class LogoutHandler(LogoutHandlerMixin, UserHandlerMixin, RedirectHandler):
    async def get(self, *args, **kwargs):
        await self.logout()
        await super().get(*args, **kwargs)


class UserTemplateHandler(UserHandlerMixin, TemplateHandler):
    """User aware TemplateHandler."""
