class InvalidChannelLayerError(ValueError):
    """
    Raised when a channel layer is configured incorrectly.
    """


class ChannelFull(Exception):
    """
    Raised when a channel cannot be sent to as it is over capacity.
    """
