import copy
import nbformat

from .log import logger
from .exceptions import PapermillMissingParameterException
from .iorw import read_yaml_file
from .translators import translate_parameters
from .utils import find_first_tagged_cell_index

from uuid import uuid4
from datetime import datetime


def add_builtin_parameters(parameters):
    """Add built-in parameters to a dictionary of parameters

    Parameters
    ----------
    parameters : dict
       Dictionary of parameters provided by the user
    """
    with_builtin_parameters = {
        "pm": {
            "run_uuid": str(uuid4()),
            "current_datetime_local": datetime.now(),
            "current_datetime_utc": datetime.utcnow(),
        }
    }

    if parameters is not None:
        with_builtin_parameters.update(parameters)

    return with_builtin_parameters


def parameterize_path(path, parameters):
    """Format a path with a provided dictionary of parameters

    Parameters
    ----------
    path : string
       Path with optional parameters, as a python format string
    parameters : dict
       Arbitrary keyword arguments to fill in the path
    """
    if parameters is None:
        parameters = {}

    try:
        return path.format(**parameters)
    except KeyError as key_error:
        raise PapermillMissingParameterException("Missing parameter {}".format(key_error))


def parameterize_notebook(nb, parameters, report_mode=False, comment='Parameters'):
    """Assigned parameters into the appropriate place in the input notebook

    Parameters
    ----------
    nb : NotebookNode
       Executable notebook object
    parameters : dict
       Arbitrary keyword arguments to pass as notebook parameters
    report_mode : bool, optional
       Flag to set report mode
    comment : str, optional
        Comment added to the injected cell
    """
    # Load from a file if 'parameters' is a string.
    if isinstance(parameters, str):
        parameters = read_yaml_file(parameters)

    # Copy the nb object to avoid polluting the input
    nb = copy.deepcopy(nb)

    kernel_name = nb.metadata.kernelspec.name
    language = nb.metadata.kernelspec.language

    # Generate parameter content based on the kernel_name
    param_content = translate_parameters(kernel_name, language, parameters, comment)

    newcell = nbformat.v4.new_code_cell(source=param_content)
    newcell.metadata['tags'] = ['injected-parameters']

    if report_mode:
        newcell.metadata['jupyter'] = newcell.get('jupyter', {})
        newcell.metadata['jupyter']['source_hidden'] = True

    param_cell_index = find_first_tagged_cell_index(nb, 'parameters')
    injected_cell_index = find_first_tagged_cell_index(nb, 'injected-parameters')
    if injected_cell_index >= 0:
        # Replace the injected cell with a new version
        before = nb.cells[:injected_cell_index]
        after = nb.cells[injected_cell_index + 1 :]
    elif param_cell_index >= 0:
        # Add an injected cell after the parameter cell
        before = nb.cells[: param_cell_index + 1]
        after = nb.cells[param_cell_index + 1 :]
    else:
        # Inject to the top of the notebook
        logger.warning("Input notebook does not contain a cell with tag 'parameters'")
        before = []
        after = nb.cells

    nb.cells = before + [newcell] + after
    nb.metadata.papermill['parameters'] = parameters

    return nb
