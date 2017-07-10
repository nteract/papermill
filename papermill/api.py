import io
import nbformat
from IPython.display import display


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


def fetch_record(cell, name):
    """
    Fetches a recorded value from the cell under inspection.

    Args:
        cell (nbformat.NotebookNode): The cell to pull the value from.
        name (str): Then name of the value.

    Returns:
        The value retrieved from the cell's output at the specified name.

    """
    value = None
    for output in cell.get('outputs', []):
        if 'data' in output and RECORD_OUTPUT_TYPE in output['data']:
            if name in output['data'][RECORD_OUTPUT_TYPE]:
                value = output['data'][RECORD_OUTPUT_TYPE][name]
    return value


def _split_bucket_and_prefix(path):
    """
    splits an s3 path into bucket and prefix, like os.path.split, only it can only be used once
    ie s3://foo/bar/baz would return ['foo','bar/baz']
    note: because a trailing / is significant in s3, it will not be stripped,
        ie s3://foo/bar/baz/ will return ['foo','bar/baz/']
    """
    if not path.startswith('s3://'):
        raise ValueError('path must start with s3://')
    path = path[5:]
    if path:
        if '/' in path:
            return path.split('/', 1)
        else:
            return [path, '']
    else:
        return ['', '']


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
