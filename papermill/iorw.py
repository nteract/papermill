import io
import nbformat

from papermill import __version__


def read_notebook(notebook_path):
    """Returns a notebook object with papermill metadata loaded from the specified path.

    Args:
        notebook_path (str): Path to the notebook file.

    Returns:
        nbformat.NotebookNode

    """
    nb = _notebook_accessors['reader'](notebook_path)

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


def save_notebook(nb, notebook_path):
    """Saves a notebook object to the specified path.

    Args:
        nb (nbformat.NotebookNode): Notebook object to save.
        notebook_path (str): Path to save the notebook object to.

    """
    _notebook_accessors['writer'](nb, notebook_path)


"""Dict for mapping notebook reader and writing fucntions."""
_notebook_accessors = {}


def _read_notebook(path):
    """Default read functionality."""
    with io.open(path, 'r') as infile:
        return nbformat.read(infile, as_version=4)


def _write_notebook(nb, path):
    """Default write functionality."""
    with io.open(path, 'w') as outfile:
        nbformat.write(nb, outfile)


def set_reader(func):
    """Interface for overwriting the notebook reader with a custom function."""
    _notebook_accessors['reader'] = func


def set_writer(func):
    """Interface for overwriting the notebook writer with a custom function."""
    _notebook_accessors['writer'] = func

# Set default Notebook accessors
set_reader(_read_notebook)
set_writer(_write_notebook)
