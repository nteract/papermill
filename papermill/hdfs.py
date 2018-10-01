import pyarrow as pa
import logging
from .utils import retry

logger = logging.getLogger('papermill.hdfs')

# python 2 compatibility imports

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class HDFS(object):
    """
           :param host: the ip address or hostname of the HDFS namenode
           :param port: the port number for WebHDFS on the namenode
           :param user: HDFS user name used for authentication
           :param kerb_ticket: kerberos tickets for authenticating
           :param **kwargs for handling extra parameters following.
           >>> fs = pa.hdfs.connect(host='host',port='50070', user='hdfs', kerb_ticket=None, **kwargs)
       """

    def __init__(self, host=None, port=None, user=None, kerb_ticket=None, driver=None, **kwargs):
        self.fs = pa.hdfs.connect(host, port, user=user, kerb_ticket=kerb_ticket, driver=driver, **kwargs)

    def path_separator(self):
        """:returns the path separator /"""
        return '/'

    def path_basename(self, path):
        """:param path:str
           :returns base path of the given path"""
        base_path = path.split(self.path_separator)[:-1]
        return '/'.join(base_path)

    def is_connected(self):
        """:returns true if the connection is made to webhdfs else returns false"""
        return self.fs is not None

    def disconnect(self):
        """disconnects from webhdfs"""
        self.fs = None

    def get_free_disk_space(self):
        return self.fs.df()

    def read(self, path):
        if self.fs.exists(path):
            with self.fs.open(path, mode='r') as f:
                return f.read()
        else:
            raise FileNotFoundError("file {path} doesn't exist".format(path=path))

    def write(self, path, content=None):
        with self.fs.open(path, mode='w') as f:
            f.write(content)

    def remove(self, path, recursive=False):
        if self.fs.exists(path):
            self.fs.rm(path, recursive)
        else:
            logger.warn("path {path} doesn't exist".format(path=path))

    def append(self, path, content=None):
        if self.fs.exists(self.path_basename(path)):
            with self.fs.open(path, 'a+') as f:
                f.write(content)
        else:
            raise FileNotFoundError("parent path {path} doesn't exist".format(path=self.path_basename(path)))

    @retry(3)
    def list(self, path, detail = False):
        if self.fs.exists(path):
            return self.fs.ls(path, detail)
        else:
            raise FileNotFoundError("directory {path} doesn't exist".format(path=path))


