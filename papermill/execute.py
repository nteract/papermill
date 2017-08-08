import os
import shutil
import tempfile
import time

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

from papermill.conf import settings
from papermill.exceptions import PapermillException
from papermill.iorw import load_notebook_node, write_ipynb, read_yaml_file

from six import string_types


def execute_notebook(notebook, output, parameters=None):
    """Executes a single notebook locally.

    Args:
        notebook (str): Path to input notebook.
        output (str): Path to save exexuted notebook.
        parameters: (dict) Arbitrary keyword arguments to pass to the notebook parameters.

    """
    if isinstance(parameters, string_types):
        parameters = read_yaml_file(parameters)

    parameters = parameters or {}
    _execute_notebook(notebook, output, parameters)


def _parameterize_notebook(nb, parameters):
    if not parameters:
        return

    param_content = _python27_param_content(parameters)
    parameters_index = find_parameters_index(nb)
    old_parameters = nb.cells[parameters_index]
    before = nb.cells[:parameters_index]
    after = nb.cells[parameters_index + 1:]
    newcell = nbformat.v4.new_code_cell(source=param_content)
    newcell.metadata['tags'] = old_parameters.metadata.tags
    nb.cells = before + [newcell] + after


def _execute_notebook(notebook_path, output_path, parameters, kernel_name=None):

    t0 = time.time()
    # Find `parameters` cell and replaced with our parameters.
    nb = load_notebook_node(notebook_path)

    _parameterize_notebook(nb, parameters)
    processor = ExecutePreprocessor(
        timeout=None,
        kernel_name=kernel_name or nb.metadata.kernelspec.name
    )
    processor.preprocess(nb, {})

    duration = time.time() - t0

    # Record specified environment variable values.
    nb.metadata.papermill['parameters'] = parameters
    nb.metadata.papermill['environment_variables'] = _fetch_environment_variables()
    nb.metadata.papermill['metrics']['duration'] = duration
    write_ipynb(nb, output_path)


def find_parameters_index(nb):
    parameters_indices = []
    for idx, cell in enumerate(nb.cells):
        if "parameters" in cell.metadata.tags:
            parameters_indices.append(idx)
    if not parameters_indices:
        raise PapermillException("No parameters tag found")
    elif len(parameters_indices) > 1:
        raise PapermillException("Multiple parameters tags found")
    return parameters_indices[0]


def _fetch_environment_variables():
    ret = dict()
    for name, value in os.environ.items():
        if name in settings.ENVIRONMENT_VARIABLES:
            ret[name] = value
    return ret


def _python27_param_content(parameters):
    # Pull out variable names and values from the parameters argument.
    if not parameters:
        return None

    param_content = "# Parameters\n"
    for var, val in parameters.items():
        if isinstance(val, string_types):
            val = '"%s"' % val  # TODO: Handle correctly escaping input strings.
        param_content += '%s = %s\n' % (var, val)
    return param_content
