# -*- coding: utf-8 -*-
"""Utilities for working with HDFS."""
import logging

from pywebhdfs.errors import FileNotFound
from pywebhdfs.webhdfs import PyWebHdfsClient

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
        :param user_name: WebHDFS user.name used for authentication
        :param path_to_hosts: mapping paths to hostnames for federation
        :param **kwargs for handling extra parameters following.
        timeout: timeout for the underlying HTTP request
        base_uri_pattern: format string for base URI
        request_extra_opts: dictionary of extra options to pass
          to the requests library (e.g., SSL, HTTP authentication, etc.)
        >>> hdfs = PyWebHdfsClient(host='host',port='50070', user_name='hdfs')
    """

    def __init__(self, host=None, port=None, user_name=None,
                 path_to_hosts=None, **kwargs):
        self.__webhdfs = PyWebHdfsClient.__init__(self, host, port, user_name, **kwargs)

    def path_separator(self):
        """:returns the path separator /"""
        return '/'

    def is_connected(self):
        """:returns true if the connection is made to webhdfs else returns false"""
        return self.__webhdfs is not None

    def disconnect(self):
        """disconnects from webhdfs"""
        self.__webhdfs = None

    def exists(self, path):
        """:param path:str hdfs path which needs to be checked if exists.
           :returns if the given directory or file exists"""
        try:
            self.__webhdfs.get_file_dir_status(path)
            return True
        except FileNotFound:
            return False

    def is_dir(self, path):
        """:param path:str path which needs to be checked if it's a directory
           :returns true if the given path is directory"""
        try:
            file_status = self.__webhdfs.get_file_dir_status(path)
            return file_status['FileStatus']['type'] == 'DIRECTORY'
        except FileNotFound:
            return False

    def is_file(self, path):
        """:param path:str path which needs to be checked if it's a directory
           :returns true if the given path is file"""
        try:
            file_status = self.__webhdfs.get_file_dir_status(path)
            return file_status['FileStatus']['type'] == 'FILE'
        except FileNotFound:
            return False

    def is_empty(self, path):
        """:param path:str path which needs to be checked if it's a directory
           :returns true if the given path is empty else false"""
        if self.exists(path):
            file_status = self.__webhdfs.get_file_dir_status(path)
            if len(file_status) > 0:
                return False
            else:
                return True


    def path_basename(self, path):
        """:param path:str
           :returns base path of the given path"""
        base_path = path.split(self.path_separator)[:-1]
        return '/'.join(base_path)


    @retry(3)
    def list(self, path):
        """:param path:str
           :returns lists the files in the directory"""
        if self.exists(path) and not self.is_file(path):
            hdfs_files = self.__webhdfs.list_dir(path)
            if not path.endswith('/'):
                path += '/'
            for f in hdfs_files['FileStatuses']['FileStatus']:
                yield path + f['pathSuffix']
        else:
            raise FileNotFound("directory {directory} doesn't exist".format(directory=path))


    def read(self, path, size=None, offset=0, binary=False):
        """:param path:str
           :returns reads contents of the given file path and returns"""
        if self.exists(path) and not self.is_file(path):
            raise FileNotFoundError("file {path} doesn't exist".format(path=path))
        read = self.__webhdfs.read_file(path, offset=offset)
        if not binary:
            read = read.decode('utf-8')
        return read


    def write(self, path, s=""):
        """:param path:str
           :returns writes the given content to file. By default it'll overwrite the existing file's
        contents. Can be disabled."""
        if not self.exists(path) and self.exists(self.path_basename(path)):
            return self.__webhdfs.create_file(path, s, overwrite=True)
        else:
            raise FileNotFound("parent directory {} doesn't exist".format(self.path_basename(path)))


    def mkdir(self, path, recursive, exist_ok=False):
        """:param path:str
           creates the directory in hdfs"""
        if not recursive and not self.is_dir(self.path_basename(path)):
            raise IOError("No parent directory found for {}.".format(path))
        if not exist_ok and self.exists(path):
            raise IOError("Path already exists at {}.".format(path))
        self.__webhdfs.make_dir(path)


    def remove(self, path, recursive):
        """:param path:str
           deletes the given path from hdfs"""
        if self.exists(path):
            if self.is_dir(path) and not self.is_empty(path) and not recursive:
                raise IOError("Folder {folder} is not empty, pass recursive True".format(folder=path))
            elif self.is_dir(path) and self.is_empty(path):
                self.__webhdfs.delete_file_dir(path, True)
                logger.info("path {folder} is delted".format(folder=path))
            elif self.is_file(path):
                self.__webhdfs.delete_file_dir(path, False)
                logger.info("file {path} is deleted".format(path=path))
        else:
            raise FileNotFound("Path {path} doesn't exist".format(path=path))

        def append(self, path, s, binary):
            """:param path:str
               appends given content to a file if exists"""
            if self.exists(path) and self.is_file(path):
                return self.__webhdfs.append_file(path, s)
            else:
                raise FileNotFound("File {path} doesn't exist".format(path=path))
