from .s3 import retry

import requests
from six.moves import http_client

import logging

from pywebhdfs.errors import FileNotFound
from pywebhdfs.webhdfs import (PyWebHdfsClient, _is_standby_exception,
                               _move_active_host_to_head)

logger = logging.getLogger('papermill.hdfs')

# python 2 compatibility imports

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class HDFS(object):
    def __init__(self, host=None, port=None, user_name=None,
                 path_to_hosts=None, **kwargs):
        self.__webhdfs = PyWebHdfsClient.__init__(self, host, port, user_name, **kwargs)

    def _path_separator(self):
        return '/'

    def _is_connected(self):
        return self.__webhdfs is not None

    def _disconnect(self):
        self.__webhdfs = None

    def _exists(self, path):
        try:
            self.__webhdfs.get_file_dir_status(path)
            return True
        except FileNotFound:
            return False

    def _is_dir(self, path):
        try:
            file_status = self.__webhdfs.get_file_dir_status(path)
            return file_status['FileStatus']['type'] == 'DIRECTORY'
        except FileNotFound:
            return False

    def _is_file(self, path):
        try:
            file_status = self.__webhdfs.get_file_dir_status(path)
            return file_status['FileStatus']['type'] == 'FILE'
        except FileNotFound:
            return False

    def _path_basename(self, path):
        base_path = path.split(self._path_separator)[:-1]
        return '/'.join(base_path)

    @retry(3)
    def _list(self, path):
        if self._exists(path) and not self._is_file(path):
            hdfs_files = self.__webhdfs.list_dir(path)
            if not path.endswith('/'):
                path += '/'
            for f in hdfs_files['FileStatuses']['FileStatus']:
                yield path + f['pathSuffix']
        else:
            raise FileNotFound("directory {directory} doesn't exist".format(directory=path))

    def _read(self, path, size=-1, offset=0, binary=False):
        if self._exists(path) and not self._is_file(path):
            raise IOError("file {path} doesn't exist".format(path=path))
        read = self.__webhdfs.read_file(path, offset=offset, length='null' if size < 0 else size)
        if not binary:
            read = read.decode('utf-8')
        return read

    def _write(self, path, s=""):
        if not self._exists(path) and self._exists(self._path_basename(path)):
            return self.__webhdfs.create_file(path, s, overwrite=True)
        else:
            raise FileNotFound("parent directory {} doesn't exist".format(self._path_basename(path)))

    def _mkdir(self, path, recursive, exist_ok=False):
        if not recursive and not self._is_dir(self._path_basename(path)):
            raise IOError("No parent directory found for {}.".format(path))
        if not exist_ok and self._exists(path):
            raise IOError("Path already exists at {}.".format(path))
        self.__webhdfs.make_dir(path)

    def _remove(self, path, recursive):
        if self._exists(path):
            if self._is_dir(path) and not self._is_empty(path) and not recursive:
                raise IOError("Folder {folder} is not empty, pass recursive True".format(folder=path))
            elif self._is_dir(path) and self._is_empty(path):
                self.__webhdfs.delete_file_dir(path, True)
                logger.info("path {folder} is delted".format(folder=path))
            elif self._is_file(path):
                self.__webhdfs.delete_file_dir(path, False)
                logger.info("file {path} is deleted".format(path=path))
        else:
            raise FileNotFound("Path {path} doesn't exist".format(path=path))

    def _append(self, path, s, binary):
        if self._exists(path) and self._is_file(path):
            return self.__webhdfs.append_file(path, s)
        else:
            raise FileNotFound("File {path} doesn't exist".format(path=path))
