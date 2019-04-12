class BasePermission:
    def __init__(self, user):
        self.user = user

    def has_permission(self, action):
        raise NotImplementedError


class AllowAny:
    def has_permission(self, action):
        return True


class IsAuthenticated(BasePermission):
    def has_permission(self, action):
        return self.user.id is not None and self.user.is_authenticated()
