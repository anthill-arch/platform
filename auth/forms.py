from anthill.framework.auth.forms import AuthenticationForm as BaseAuthenticationForm
from anthill.platform.auth import internal_authenticate as authenticate, RemoteUser
from anthill.platform.api.internal import RequestError, RequestTimeoutError


class AuthenticationForm(BaseAuthenticationForm):
    async def authenticate(self, internal_request=None) -> RemoteUser:
        user = await authenticate(internal_request, **self.get_credentials())
        if not user:
            self.invalid_login_error()
        else:
            self.confirm_login_allowed(user)
        return user
