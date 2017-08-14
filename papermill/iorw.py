import io
import os

import nbformat
import yaml

from papermill import __version__


class PapermillIO(object):

    @staticmethod
    def read(path):
        with io.open(path, 'r') as f:
            return f.read()

    @staticmethod
    def listdir(path):
        return [os.path.join(path, fn) for fn in os.listdir(path)]

    @staticmethod
    def write(buf, path):
        with io.open(path, 'w') as f:
            f.write(buf)

    def register(self, name, func):
        if hasattr(self, name):
            setattr(self, name, func)
        else:
            raise ValueError("No I/O method called '%s'." % name)


papermill_io = PapermillIO()


def register_io(name):
    """Decorator for registering custom io functions for papermill."""
    def wrapper(func):
        papermill_io.register(name, func)
        return func
    return wrapper


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
            'metrics': dict(),
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
