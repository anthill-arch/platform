import tempfile
import os


class PrivateSSHKeyContext:
    """
    Usage:
        with PrivateSSHKeyContext("private ssh key string") as key_file:
            ...
    """

    def __init__(self, key_data=None):
        self._data = key_data
        self._f = None

    def __enter__(self):
        if self._data is None:
            return None

        self._f = tempfile.NamedTemporaryFile(delete=False)

        self._f.write(self._data)
        self._f.write('\n')
        self._f.close()

        return self._f.name

    def __exit__(self, *exc_info):
        if self._f:
            os.unlink(self._f.name)
