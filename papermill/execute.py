import os
import time

import nbformat
from jupyter_client.kernelspec import get_kernel_spec
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.preprocessors.execute import CellExecutionError

from papermill.conf import settings
from papermill.exceptions import PapermillException
from papermill.iorw import load_notebook_node, write_ipynb, read_yaml_file

from six import string_types


class PapermillExecutePreprocessor(ExecutePreprocessor):

    def preprocess(self, nb, resources):
        """
        The default preprocess behavior if allow_errors = True is to continue executing all the cells.
        We want the notebook to cease execution and then write out the state of the notebook with the traceback
        on the cell that failed.
        """
        # Clear out all outputs prior to execution.
        for cell in nb.cells:
            cell.outputs = []

        # Catch CellExecutionError if thrown which lets this method finish so we can write the state of the notebook
        # to disk.
        try:
            nb, resources = super(PapermillExecutePreprocessor, self).preprocess(nb, resources)
        except CellExecutionError:
            pass

        return nb, resources


def execute_notebook(notebook, output, parameters=None, kernel_name=None):
    """Executes a single notebook locally.

    Args:
        notebook (str): Path to input notebook.
        output (str): Path to save exexuted notebook.
        parameters (dict): Arbitrary keyword arguments to pass to the notebook parameters.
        kernel_name (str): Name of kernel to execute the notebook against.

    """
    nb = load_notebook_node(notebook)

    # Parameterize the Notebook.
    if parameters:
        _parameterize_notebook(nb, kernel_name, parameters)

    # Execute the Notebook.
    t0 = time.time()
    processor = PapermillExecutePreprocessor(
        timeout=None,
        kernel_name=kernel_name or nb.metadata.kernelspec.name,
    )
    processor.preprocess(nb, {})
    duration = time.time() - t0

    # Record specified environment variable values.
    nb.metadata.papermill['parameters'] = parameters
    nb.metadata.papermill['environment_variables'] = _fetch_environment_variables()
    nb.metadata.papermill['metrics']['duration'] = duration

    # Write Notebook to disk.
    write_ipynb(nb, output)


def _parameterize_notebook(nb, kernel_name, parameters):

    # Load from a file if 'parameters' is a string.
    if isinstance(parameters, string_types):
        parameters = read_yaml_file(parameters)

    # Generate parameter content based on the kernal_name
    kernel_name = kernel_name or nb.metadata.kernelspec.name
    param_content = _build_parameter_code(kernel_name, parameters)

    # Remove the old cell and replace it with a new one containing parameter content.
    param_cell_index = _find_parameters_index(nb)
    old_parameters = nb.cells[param_cell_index]
    before = nb.cells[:param_cell_index]
    after = nb.cells[param_cell_index + 1:]
    newcell = nbformat.v4.new_code_cell(source=param_content)
    newcell.metadata['tags'] = old_parameters.metadata.tags
    nb.cells = before + [newcell] + after


def _build_parameter_code(kernel_name, parameters):
    kernelspec = get_kernel_spec(kernel_name)
    if kernel_name in _parameter_code_builders:
        return _parameter_code_builders[kernel_name](parameters)
    elif kernelspec.language in _parameter_code_builders:
        return _parameter_code_builders[kernelspec.language](parameters)
    raise PapermillException(
        "No parameter builder functions specified for kernel '%s' or language '%s'" % (kernel_name, kernelspec.language)
    )


def _find_parameters_index(nb):
    parameters_indices = []
    for idx, cell in enumerate(nb.cells):
        if "parameters" in cell.metadata.tags:
            parameters_indices.append(idx)
    if not parameters_indices:
        raise PapermillException("No parameters tag found")
    elif len(parameters_indices) > 1:
        raise PapermillException("Multiple parameters tags found")
    return parameters_indices[0]


# Registry for functions that build parameter assignment code.
_parameter_code_builders = {}


def register_param_builder(name):
    """Decorator for registering functions that write variable assignments for a given kernel or language."""
    def wrapper(func):
        _parameter_code_builders[name] = func
        return func
    return wrapper


@register_param_builder("python")
def build_python_params(parameters):
    """Writers parameter assignment code for Python kernels."""
    param_content = "# Parameters\n"
    for var, val in parameters.items():
        if isinstance(val, string_types):
            val = '"%s"' % val  # TODO: Handle correctly escaping input strings.
        param_content += '%s = %s\n' % (var, val)
    return param_content


@register_param_builder("R")
def build_r_params(parameters):
    """Writes parameters assignment code for R kernels."""
    param_content = "# Parameters\n"
    for var, val in parameters.items():
        if isinstance(val, string_types):
            val = '"%s"' % val  # TODO: Handle correctly escaping input strings.
        elif val is True:
            val = 'TRUE'
        elif val is False:
            val = 'FALSE'
        param_content += '%s = %s\n' % (var, val)
    return param_content


def _fetch_environment_variables():
    ret = dict()
    for name, value in os.environ.items():
        if name in settings.ENVIRONMENT_VARIABLES:
            ret[name] = value
    return ret
