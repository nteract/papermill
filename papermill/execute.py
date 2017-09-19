import datetime
import os

import nbformat
from concurrent import futures
from jupyter_client.kernelspec import get_kernel_spec
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.preprocessors.execute import CellExecutionError
from nbconvert.preprocessors.base import Preprocessor

from papermill.conf import settings
from papermill.exceptions import PapermillException, PapermillExecutionError
from papermill.iorw import load_notebook_node, write_ipynb, read_yaml_file

from six import string_types

PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"


def preprocess(self, nb, resources):
    """
    This function monkey patches the Preprocessor.preprocess method.

    We are doing this for the following reasons:
    1. Notebooks will stop executing when they encounter a failure but not raise a CellException.
       This allows us to save the notebook with the traceback even though a CellExecutionError
       was encountered.

    2. We want to write the notebook as cells are executed. We inject our logic for that here.

    3. We want to include timing and execution status information with the metadata of each cell.

    Parameters
    ----------
    nb : NotebookNode
        Notebook being converted
    resources : dictionary
        Additional resources used in the conversion process.  Allows
        preprocessors to pass variables into the Jinja engine.
    """
    output_path = nb.metadata.papermill['output_path']

    # Reset the notebook.
    for cell in nb.cells:
        # Reset the cell execution counts.
        if cell.get("execution_count") is not None:
            cell.execution_count = None

        # Clear out the papermill metadata for each cell.
        cell.metadata['papermill'] = dict(
            exception=None,
            start_time=None,
            end_time=None,
            duration=None,
            status=PENDING  # pending, running, completed
        )
        if cell.get("outputs") is not None:
            cell.outputs = []

    # Execute each cell and update the output in real time.
    with futures.ThreadPoolExecutor(max_workers=1) as executor:
        for index, cell in enumerate(nb.cells):
            cell.metadata["papermill"]["status"] = RUNNING
            future = executor.submit(write_ipynb, nb, output_path)
            t0 = datetime.datetime.utcnow()
            try:
                nb.cells[index], resources = self.preprocess_cell(cell, resources, index)
                cell.metadata['papermill']['exception'] = False
            except CellExecutionError:
                cell.metadata['papermill']['exception'] = True
                break
            finally:
                t1 = datetime.datetime.utcnow()
                cell.metadata['papermill']['start_time'] = t0.isoformat()
                cell.metadata['papermill']['end_time'] = t1.isoformat()
                cell.metadata['papermill']['duration'] = (t1 - t0).total_seconds()
                cell.metadata['papermill']['status'] = COMPLETED
                future.result()
    return nb, resources


# Monkey Patch the base preprocess method.
Preprocessor.preprocess = preprocess


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

    # Record specified environment variable values.
    nb.metadata.papermill['parameters'] = parameters
    nb.metadata.papermill['environment_variables'] = _fetch_environment_variables()
    nb.metadata.papermill['output_path'] = output

    # Execute the Notebook.
    t0 = datetime.datetime.utcnow()
    processor = ExecutePreprocessor(
        timeout=None,
        kernel_name=kernel_name or nb.metadata.kernelspec.name,
    )
    processor.preprocess(nb, {})
    t1 = datetime.datetime.utcnow()

    nb.metadata.papermill['start_time'] = t0.isoformat()
    nb.metadata.papermill['end_time'] = t1.isoformat()
    nb.metadata.papermill['duration'] = (t1 - t0).total_seconds()
    nb.metadata.papermill['exception'] = any([cell.metadata.papermill.get('exception') for cell in nb.cells])

    # Write final Notebook to disk.
    write_ipynb(nb, output)
    raise_for_execution_errors(nb, output)


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


ERROR_MESSAGE_TEMPLATE = (
    '<span style="color:red; font-family:Helvetica Neue, Helvetica, Arial, sans-serif; font-size:2em;">'
    "An Exception was encountered at 'In [%s]'."
    '</span>'
)


def raise_for_execution_errors(nb, output_path):

    error = None
    for cell in nb.cells:
        if cell.get("outputs") is None:
            continue

        for output in cell.outputs:
            if output.output_type == "error":
                error = PapermillExecutionError(
                    exec_count=cell.execution_count,
                    source=cell.source,
                    ename=output.ename,
                    evalue=output.evalue,
                    traceback=output.traceback
                )
            break

    if error:
        # Write notebook back out with the Error Message at the top of the Notebook.
        error_msg = ERROR_MESSAGE_TEMPLATE % str(error.exec_count)
        error_msg_cell = nbformat.v4.new_markdown_cell(source=error_msg)
        nb.cells = [error_msg_cell] + nb.cells
        write_ipynb(nb, output_path)
        raise error
