 # -*- coding: utf-8 -*-

from __future__ import unicode_literals

import io
import json
import os

import nbformat
import requests
import yaml

from . import __version__
from .exceptions import PapermillException
from .s3 import S3


class PapermillIO(object):
    def __init__(self):
        self.reset()

    def read(self, path):
        return self.get_handler(path).read(path)

    def write(self, buf, path):
        # Usually no return object here
        return self.get_handler(path).write(buf, path)

    def listdir(self, path):
        return self.get_handler(path).listdir(path)

    def pretty_path(self, path):
        return self.get_handler(path).pretty_path(path)

    def reset(self):
        self.__handlers = []

    def register(self, scheme, handler):
        # Keep these ordered as LIFO
        self.__handlers.insert(0, (scheme, handler))

    def get_handler(self, path):
        local_handler = None
        for scheme, handler in self.__handlers:
            if scheme == 'local':
                local_handler = handler

            if path.startswith(scheme):
                return handler

        if local_handler is None:
            raise PapermillException(
                "Could not find a registered schema handler for: {}"
                .format(path))

        return local_handler


class HttpHandler(object):
    @classmethod
    def read(cls, path):
        return requests.get(path).text

    @classmethod
    def listdir(cls, path):
        raise PapermillException('listdir is not supported by HttpHandler')

    @classmethod
    def write(cls, buf, path):
        result = requests.put(path, json=json.loads(buf))
        result.raise_for_status()

    @classmethod
    def pretty_path(cls, path):
        return path


class LocalHandler(object):
    @classmethod
    def read(cls, path):
        with io.open(path, 'r', encoding="utf-8") as f:
            return f.read()

    @classmethod
    def listdir(cls, path):
        return [os.path.join(path, fn) for fn in os.listdir(path)]

    @classmethod
    def write(cls, buf, path):
        with io.open(path, 'w', encoding="utf-8") as f:
            f.write(buf)

    @classmethod
    def pretty_path(cls, path):
        return path


class S3Handler(object):

    keyname = None

    @classmethod
    def read(cls, path):
        s3_client = S3(keyname=cls.keyname)
        return "\n".join(s3_client.read(path))

    @classmethod
    def listdir(cls, path):
        s3_client = S3(keyname=cls.keyname)
        return s3_client.listdir(path)

    @classmethod
    def write(cls, buf, path):
        s3_client = S3(keyname=cls.keyname)
        return s3_client.cp_string(buf, path)

    @classmethod
    def pretty_path(cls, path):
        return path
            

# Instantiate a PapermillIO instance and register Handlers.
papermill_io = PapermillIO()
papermill_io.register("local", LocalHandler)
papermill_io.register("s3://", S3Handler)
papermill_io.register("http://", HttpHandler)
papermill_io.register("https://", HttpHandler)


def read_yaml_file(path):
    """Reads a YAML file from the location specified at 'path'."""
    return yaml.load(papermill_io.read(path))


def write_ipynb(nb, path):
    """Saves a notebook object to the specified path.
    Args:
        nb_node (nbformat.NotebookNode): Notebook object to save.
        notebook_path (str): Path to save the notebook object to.
    """
    papermill_io.write(nbformat.writes(nb), path)


def load_notebook_node(notebook_path):
    """Returns a notebook object with papermill metadata loaded from the specified path.

    Args:
        notebook_path (str): Path to the notebook file.

    Returns:
        nbformat.NotebookNode

    """
    nb = nbformat.reads(papermill_io.read(notebook_path), as_version=4)

    if not hasattr(nb.metadata, 'papermill'):
        nb.metadata['papermill'] = {
            'version': __version__
        }

    for cell in nb.cells:
        if not hasattr(cell.metadata, 'tags'):
            # Create tags attr if one doesn't exist.
            cell.metadata['tags'] = []

    return nb


def list_notebook_files(path):
    """Returns a list of all the notebook files in a directory."""
    return [p for p in papermill_io.listdir(path) if p.endswith('.ipynb')]


def get_pretty_path(path):
    return papermill_io.pretty_path(path)
