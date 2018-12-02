# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import io
import json
import os

import nbformat
import requests
import yaml
import fnmatch
import warnings

import entrypoints

from . import __version__
from .exceptions import PapermillException
from .s3 import S3
from .adl import ADL
from .abs import AzureBlobStore

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class PapermillIO(object):
    '''
    The holder which houses any io system registered with the system.
    This object is used in a singleton manner to save and load particular
    named Handler objects for reference externally.
    '''

    def __init__(self):
        self.reset()

    def read(self, path):
        if not fnmatch.fnmatch(os.path.basename(path), "*.*"):
            warnings.warn(
                "the file is not specified with any extension : " + os.path.basename(path)
            )
        elif not (
            fnmatch.fnmatch(os.path.basename(path), "*.ipynb")
            or fnmatch.fnmatch(os.path.basename(path), "*.json")
        ):
            warnings.warn(
                "The specified input file ({}) does not end in '.ipynb' or '.json'".format(path)
            )
        return self.get_handler(path).read(path)

    def write(self, buf, path):
        # Usually no return object here
        if not fnmatch.fnmatch(os.path.basename(path), "*.*"):
            warnings.warn(
                "the file is not specified with any extension : " + os.path.basename(path)
            )
        elif not (
            fnmatch.fnmatch(os.path.basename(path), "*.ipynb")
            or fnmatch.fnmatch(os.path.basename(path), "*.json")
        ):
            warnings.warn(
                "The specified input file ({}) does not end in '.ipynb' or '.json'".format(path)
            )
        return self.get_handler(path).write(buf, path)

    def listdir(self, path):
        return self.get_handler(path).listdir(path)

    def pretty_path(self, path):
        return self.get_handler(path).pretty_path(path)

    def reset(self):
        self._handlers = []

    def register(self, scheme, handler):
        # Keep these ordered as LIFO
        self._handlers.insert(0, (scheme, handler))

    def register_entry_points(self):
        # Load handlers provided by other packages
        for entrypoint in entrypoints.get_group_all("papermill.io"):
            self.register(entrypoint.name, entrypoint.load())

    def get_handler(self, path):
        local_handler = None
        for scheme, handler in self._handlers:
            if scheme == 'local':
                local_handler = handler

            if path.startswith(scheme):
                return handler

        if local_handler is None:
            raise PapermillException(
                "Could not find a registered schema handler for: {}".format(path)
            )

        return local_handler


class HttpHandler(object):
    @classmethod
    def read(cls, path):
        return requests.get(path, headers={'Accept': 'application/json'}).text

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
        dirname = os.path.dirname(path)
        if dirname and not os.path.exists(dirname):
            raise FileNotFoundError("output folder {} doesn't exist.".format(dirname))
        with io.open(path, 'w', encoding="utf-8") as f:
            f.write(buf)

    @classmethod
    def pretty_path(cls, path):
        return path


class S3Handler(object):
    @classmethod
    def read(cls, path):
        return "\n".join(S3().read(path))

    @classmethod
    def listdir(cls, path):
        return S3().listdir(path)

    @classmethod
    def write(cls, buf, path):
        return S3().cp_string(buf, path)

    @classmethod
    def pretty_path(cls, path):
        return path


class ADLHandler(object):
    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            cls._client = ADL()
        return cls._client

    @classmethod
    def read(cls, path):
        lines = cls._get_client().read(path)
        return "\n".join(lines)

    @classmethod
    def listdir(cls, path):
        return cls._get_client().listdir(path)

    @classmethod
    def write(cls, buf, path):
        return cls._get_client().write(buf, path)

    @classmethod
    def pretty_path(cls, path):
        return path


class ABSHandler(object):
    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            cls._client = AzureBlobStore()
        return cls._client

    @classmethod
    def read(cls, path):
        lines = cls._get_client().read(path)
        return "\n".join(lines)

    @classmethod
    def listdir(cls, path):
        return cls._get_client().listdir(path)

    @classmethod
    def write(cls, buf, path):
        return cls._get_client().write(buf, path)

    @classmethod
    def pretty_path(cls, path):
        return path


# Instantiate a PapermillIO instance and register Handlers.
papermill_io = PapermillIO()
papermill_io.register("local", LocalHandler)
papermill_io.register("s3://", S3Handler)
papermill_io.register("adl://", ADLHandler)
papermill_io.register("abs://", ABSHandler)
papermill_io.register("http://", HttpHandler)
papermill_io.register("https://", HttpHandler)
papermill_io.register_entry_points()


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
            'parameters': dict(),
            'environment_variables': dict(),
            'version': __version__,
        }

    for cell in nb.cells:
        if not hasattr(cell.metadata, 'tags'):
            cell.metadata['tags'] = []  # Create tags attr if one doesn't exist.

        if not hasattr(cell.metadata, 'papermill'):
            cell.metadata['papermill'] = dict()
    return nb


def list_notebook_files(path):
    """Returns a list of all the notebook files in a directory."""
    return [p for p in papermill_io.listdir(path) if p.endswith('.ipynb')]


def get_pretty_path(path):
    return papermill_io.pretty_path(path)
