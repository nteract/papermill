import io
import os

import nbformat
import pandas as pd
from IPython.display import display
from six import string_types


RECORD_OUTPUT_TYPE = 'application/papermill.record+json'


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
            'environment_variables': dict(),
            'duration': 0.0,
            'schema_version': 0
        }

    for cell in nb.cells:
        if not hasattr(cell.metadata, 'tags'):
            cell.metadata['tags'] = []  # Create tags attr if one doesn't exist.

        if not hasattr(cell.metadata, 'papermill'):
            cell.metadata['papermill'] = dict()
    return nb


def read_notebooks(notebook_dir):
    """Returns a list of NotebookNode objects read in from the directory specified at notebook_dir.

    Args:
        notebook_dir (str): Path to the notebooks directory.

    Returns:
        List of NotebookNode objects.

    """
    nbs = {}
    for filename in os.listdir(notebook_dir):
        notebook_path = os.path.join(notebook_dir, filename)
        if notebook_path.endswith('.ipynb'):
            nbs[filename] = read_notebook(notebook_path)
    return nbs


def save_notebook(nb, notebook_path):
    """Saves a notebook object to the specified path.

    Args:
        nb (nbformat.NotebookNode): Notebook object to save.
        notebook_path (str): Path to save the notebook object to.

    """
    _notebook_accessors['writer'](nb, notebook_path)


def display_image(image):
    display(image, raw=True)


def get_tagged_cell(nb, tag, index=0):
    """
    Returns a single cell containing the input tag.

    Args:
        nb (nbformat.NotebookNode): Notebook under inspection.
        tag (str): The tag the cell contains.
        index (int): Optional index to select something other than the first matching cell if there is more than one.

    Returns:
        nbformat.NotebookNode: A cell nbformat.NotebookNode object.

    """
    cells = get_tagged_cells(nb, tag)
    return cells[index] if cells else None


def get_tagged_cells(nb, tag):
    """
    Returns a list of cells found in the notebook that contain the specified tag.

    Args:
        nb (nbformat.NotebookNode): Notebook under inspection.
        tag (str): The tag the cell contains.

    Returns:
        list(nbformat.NotebookNode): A list of cells.

    """
    return [c for c in nb.cells if tag in c.metadata.tags]


def get_image_from_cell(cell, index=0):
    """
    Returns a single image output from an notebook cell.

    Args:
        cell (nbformat.NotebookNode): The cell with outputs containing the image.
        index (int): The index of the image if there is more than one.

    Returns:
        nbformat.NotebookNode: The nbformat.NotebookNode output for the image.

    """
    images = get_images_from_cell(cell)
    return images[index] if images else None


def get_images_from_cell(cell):
    """
    Returns a list of image outputs for a given cell.

    Args:
        cell (nbformat.NotebookNode): The cell with outputs containing the image.

    Returns:
        list(nbformat.NotebookNode): A list of image outputs

    """
    return [o['data'] for o in cell.get('outputs', []) if 'data' in o and 'image/png' in o['data']]


def display_tagged_cell_image(nb, tag, cell_index=0, image_index=0):
    """
    Displays the output from a nbformat.NotebookNode and displays it in the executing cell.

    Args:
        nb (nbformat.NotebookNode): Notebook under inspection.
        tag (str): The tag the cell contains.
        cell_index (int): The index of the cell if there are more than one.
        image_index (int): The index of the image output if there are more than one.

    """
    cell = get_tagged_cell(nb, tag, index=cell_index)
    image = get_image_from_cell(cell, index=image_index)
    display_image(image)


def record_value(name, value):
    """
    Records the value as part of the executing cell's output to be retrieved during inspection.

    Args:
        name (str): Name of the value
        value: The value to record.

    """
    display({RECORD_OUTPUT_TYPE: {name: value}}, raw=True)


def fetch_notebook_data(notebook):
    """
    Returns a dict of all the recorded data from the execution of the notebook.

    Args:
        notebook (nbformat.NotebookNode or str): Notebook or path to notebook under inspection.

    Returns:
        Dictionary of parameters for the notebook and the recorded notebook data.
    """
    if isinstance(notebook, string_types):
        # Pull from path if notebook is a string.
        nb = read_notebook(notebook)
    else:
        nb = notebook

    ret = {}
    ret.update(nb.metadata.papermill['parameters'])
    for cell in nb.cells:
        for output in cell.get('outputs', []):
            if 'data' in output and RECORD_OUTPUT_TYPE in output['data']:
                ret.update(output['data'][RECORD_OUTPUT_TYPE])
    return ret


def fetch_notebooks_dataframe(notebooks):
    """
    Returns a dataframe where each row is a notebook in a directory and each column is a parameter
    or recorded data value from the notebooks.

    Args:
        notebooks (list): List of NotebookNode or paths to the notebook directory.

    Returns:
        pd.DataFrame containing the data from the notebooks in the directory.
    """
    if isinstance(notebooks, string_types):
        # Pull from path if notebook is a string.
        nbs = read_notebooks(notebooks)
    else:
        nbs = notebooks

    fnames = sorted(nbs.keys())
    notebook_datas = [fetch_notebook_data(nbs[fname]) for fname in fnames]
    return pd.DataFrame(notebook_datas, index=fnames)


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
