class InternalRequestHandlerMixin:
    @property
    def internal_request(self):
        """
        An alias for `self.application.internal_connection.request
        <InternalConnection.request>`.
        """
        return self.application.internal_connection.request
