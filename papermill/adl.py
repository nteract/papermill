"""Utilities for working with Azure data lake storage"""
import re

from azure.datalake.store import core, lib


class ADL:
    """
    Represents an Azure Data Lake

    Methods
    -------
    The following are wrapped utilities for Azure storage:
    - read
    - listdir
    - write
    """

    def __init__(self):
        self.token = None

    @classmethod
    def _split_url(cls, url):
        match = re.match(r'adl://(.*)\.azuredatalakestore\.net\/(.*)$', url)
        if not match:
            raise Exception(f"Invalid ADL url '{url}'")
        else:
            return (match.group(1), match.group(2))

    def _get_token(self):
        if self.token is None:
            self.token = lib.auth()
        return self.token

    def _create_adapter(self, store_name):
        return core.AzureDLFileSystem(self._get_token(), store_name=store_name)

    def listdir(self, url):
        """Returns a list of the files under the specified path"""
        (store_name, path) = self._split_url(url)
        adapter = self._create_adapter(store_name)
        return [f"adl://{store_name}.azuredatalakestore.net/{path_to_child}" for path_to_child in adapter.ls(path)]

    def read(self, url):
        """Read storage at a given url"""
        (store_name, path) = self._split_url(url)
        adapter = self._create_adapter(store_name)
        lines = []
        with adapter.open(path) as f:
            for line in f:
                lines.append(line.decode())
        return lines

    def write(self, buf, url):
        """Write buffer to storage at a given url"""
        (store_name, path) = self._split_url(url)
        adapter = self._create_adapter(store_name)
        with adapter.open(path, 'wb') as f:
            f.write(buf.encode())
