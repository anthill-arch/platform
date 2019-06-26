from anthill.framework.core.files.storage import default_storage


class FileManager:
    def __init__(self, storage=None):
        self.storage = storage or default_storage

    # TODO: provide file system operations
