import re
from azure.datalake.store import core, lib


class ADL(object):
    def __init__(self):
        self.token = None

    @classmethod
    def _split_url(cls, url):
        match = re.match(r'adl://(.*)\.azuredatalakestore\.net\/(.*)$', url)
        if not match:
            raise Exception("Invalid ADL url '{0}'".format(url))
        else:
            return (match.group(1), match.group(2))

    def _get_token(self):
        if self.token is None:
            self.token = lib.auth()
        return self.token

    def _create_adapter(self, store_name):
        return core.AzureDLFileSystem(self._get_token(), store_name=store_name)

    def listdir(self, url):
        (store_name, path) = self._split_url(url)
        adapter = self._create_adapter(store_name)
        return adapter.ls(path)

    def read(self, url):
        (store_name, path) = self._split_url(url)
        adapter = self._create_adapter(store_name)
        lines = []
        with adapter.open(path) as f:
            for line in f:
                lines.append(line.decode())
        return lines

    def write(self, buf, url):
        (store_name, path) = self._split_url(url)
        adapter = self._create_adapter(store_name)
        with adapter.open(path, 'wb') as f:
            f.write(buf.encode())
