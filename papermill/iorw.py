import io
import os

import nbformat
import yaml

from papermill import __version__
from papermill.s3 import S3


class PapermillIO(object):

    __handlers = {}

    def read(self, path):
        return self.get_handler(path).read(path)

    def write(self, buf, path):
        self.get_handler(path).write(buf, path)

    def listdir(self, path):
        return self.get_handler(path).listdir(path)

    @classmethod
    def register(cls, scheme, handler):
        cls.__handlers[scheme] = handler

    def get_handler(self, path):
        for scheme, handler in self.__handlers.items():
            if scheme == 'local':
                continue

            if path.startswith(scheme):
                return handler
        return self.__handlers['local']


class LocalHandler(object):

    @classmethod
    def read(cls, path):
        with io.open(path, 'r') as f:
            return f.read()

    @classmethod
    def listdir(cls, path):
        return [os.path.join(path, fn) for fn in os.listdir(path)]

    @classmethod
    def write(cls, buf, path):
        with io.open(path, 'w') as f:
            f.write(buf)


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


# Instantiate a PapermillIO instance and register Handlers.
papermill_io = PapermillIO()
papermill_io.register("local", LocalHandler)
papermill_io.register("s3://", S3Handler)


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
            'version': __version__
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
