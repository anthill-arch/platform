from anthill.framework.utils.asynchronous import as_future
from pygdbmi.gdbcontroller import GdbController
import os

REQUIRED_GDB_FLAGS = ["--interpreter=mi2"]


class GDBInspector:
    """Wrapper around pygdbmi.gdbcontroller.GdbController."""

    def __init__(self, binary, corefile='core', path=None):
        self._binary = os.path.join(path, binary) if path else binary
        self._corefile = os.path.join(path, corefile) if path else corefile
        self._gdb = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.exit()

    def __getattr__(self, item):
        return getattr(self._gdb, item)

    @as_future
    def connect(self):
        self._gdb = GdbController(gdb_args=self.gdb_args)

    @as_future
    def exit(self):
        return self._gdb.exit()

    @property
    def gdb_args(self):
        args = [self._binary, self._corefile]
        args += REQUIRED_GDB_FLAGS
        return args

    @as_future
    def write(self, *args, **kwargs):
        return self._gdb.write(*args, **kwargs)

    def corefile_exists(self):
        return os.path.isfile(self._corefile)
