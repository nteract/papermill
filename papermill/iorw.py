import io
import os

import nbformat
import yaml

from papermill import __version__


def load_notebook_node(notebook_path):
    """Returns a notebook object with papermill metadata loaded from the specified path.

    Args:
        notebook_path (str): Path to the notebook file.

    Returns:
        nbformat.NotebookNode

    """
    nb = read_ipynb(notebook_path)

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


def read_ipynb(path):
    """Default read functionality."""
    with io.open(path, 'r') as infile:
        return nbformat.read(infile, as_version=4)


def write_ipynb(nb_node, notebook_path):
    """Saves a notebook object to the specified path.

    Args:
        nb_node (nbformat.NotebookNode): Notebook object to save.
        notebook_path (str): Path to save the notebook object to.

    """
    with io.open(notebook_path, 'w') as outfile:
        nbformat.write(nb_node, outfile)


def read_yaml_file(path):
    """Reads a YAML file from the location specified at 'path'."""
    with io.open(path, 'r') as infile:
        return yaml.load(infile)


def list_notebook_files(path):
    """Returns a list of all the notebook files in a directory."""
    return [os.path.join(path, fn) for fn in os.listdir(path) if fn.endswith('.ipynb')]
