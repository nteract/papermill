 # -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import datetime
import os
import sys

import nbformat
from jupyter_client.kernelspec import get_kernel_spec
from six import string_types, integer_types

from .conf import settings
from .exceptions import PapermillException, PapermillExecutionError
from .preprocess import PapermillExecutePreprocessor, no_tqdm
from .iorw import load_notebook_node, write_ipynb, read_yaml_file, get_pretty_path


def log_outputs(cell):
    execution_count = cell.get("execution_count")
    if not execution_count:
        return

    stderrs = []
    stdouts = []
    for output in cell.get("outputs", []):
        if output.output_type == "stream":
            if output.name == "stdout":
                stdouts.append("".join(output.text))
            elif output.name == "stderr":
                stderrs.append("".join(output.text))
        elif "data" in output and "text/plain" in output.data:
            stdouts.append(output.data['text/plain'])

    # Log stdouts
    sys.stdout.write('{:-<40}'.format("Out [%s] " % execution_count) + "\n")
    sys.stdout.write("\n".join(stdouts) + "\n")

    # Log stderrs
    sys.stderr.write('{:-<40}'.format("Out [%s] " % execution_count) + "\n")
    sys.stderr.write("\n".join(stderrs) + "\n")


def execute_notebook(notebook,
                     output,
                     parameters=None,
                     prepare_only=False,
                     kernel_name=None,
                     progress_bar=True,
                     log_output=False,
                     start_timeout=60):
    """Executes a single notebook locally.
    Args:
        notebook (str): Path to input notebook.
        output (str): Path to save executed notebook.
        parameters (dict): Arbitrary keyword arguments to pass to the notebook parameters.
        prepare_only (bool): Flag to determine if execution should occur or not.
        kernel_name (str): Name of kernel to execute the notebook against.
        progress_bar (bool): Flag for whether or not to show the progress bar.
        log_output (bool): Flag for whether or not to write notebook output to stderr.
        start_timeout (int): Duration to wait for kernel start-up.

    Returns:
         nb (NotebookNode): Executed notebook object
    """
    print("Input Notebook:  %s" % get_pretty_path(notebook), file=sys.stderr)
    print("Output Notebook: %s" % get_pretty_path(output), file=sys.stderr)
    nb = load_notebook_node(notebook)

    # Parameterize the Notebook.
    if parameters:
        _parameterize_notebook(nb, kernel_name, parameters)

    # Record specified environment variable values.
    nb.metadata.papermill[
        'environment_variables'] = _fetch_environment_variables()
    nb.metadata.papermill['output_path'] = output

    if not prepare_only:
        # Execute the Notebook.
        _execute_parameterized_notebook(nb,
                                        kernel_name,
                                        progress_bar,
                                        log_output,
                                        start_timeout)

    # Write final Notebook to disk.
    write_ipynb(nb, output)
    raise_for_execution_errors(nb, output)
    # always return notebook object
    return nb


def _parameterize_notebook(nb, kernel_name, parameters):
    """Assigned parameters into the appropiate place in the input notebook
    Args:
        nb (NotebookNode): Executable notebook object
        kernel_name (str): Name of kernel to execute the notebook against.
        parameters (dict): Arbitrary keyword arguments to pass to the notebook parameters.
    """
    # Load from a file if 'parameters' is a string.
    if isinstance(parameters, string_types):
        parameters = read_yaml_file(parameters)

    # Generate parameter content based on the kernal_name
    kernel_name = kernel_name or nb.metadata.kernelspec.name
    param_content = _build_parameter_code(kernel_name, parameters)

    param_cell_index = _find_parameters_index(nb)
    if param_cell_index >= 0:
        old_parameters = nb.cells[param_cell_index]
        old_parameters.metadata['tags'].remove('parameters')
        old_parameters.metadata['tags'].append('default parameters')

    newcell = nbformat.v4.new_code_cell(source=param_content)
    newcell.metadata['tags'] = ['parameters']

    before = nb.cells[:param_cell_index + 1]
    after = nb.cells[param_cell_index + 1:]
    nb.cells = before + [newcell] + after

    nb.metadata.papermill['parameters'] = parameters


def _execute_parameterized_notebook(nb,
                                    kernel_name=None,
                                    progress_bar=True,
                                    log_output=False,
                                    start_timeout=60):
    """Performs the actual execution of the parameterized notebook locally.
    Args:
        nb (NotebookNode): Executable notebook object.
        kernel_name (str): Name of kernel to execute the notebook against.
        progress_bar (bool): Flag for whether or not to show the progress bar.
        log_output (bool): Flag for whether or not to write notebook output to stderr.
        start_timeout (int): Duration to wait for kernel start-up.
    """
    t0 = datetime.datetime.utcnow()
    processor = PapermillExecutePreprocessor(
        timeout=None,
        startup_timeout=start_timeout,
        kernel_name=kernel_name or nb.metadata.kernelspec.name, )
    processor.progress_bar = progress_bar and not no_tqdm
    processor.log_output = log_output

    processor.preprocess(nb, {})
    t1 = datetime.datetime.utcnow()

    nb.metadata.papermill['start_time'] = t0.isoformat()
    nb.metadata.papermill['end_time'] = t1.isoformat()
    nb.metadata.papermill['duration'] = (t1 - t0).total_seconds()
    nb.metadata.papermill['exception'] = any(
        [cell.metadata.papermill.get('exception') for cell in nb.cells])


def _build_parameter_code(kernel_name, parameters):
    kernelspec = get_kernel_spec(kernel_name)
    if kernel_name in _parameter_code_builders:
        return _parameter_code_builders[kernel_name](parameters)
    elif kernelspec.language in _parameter_code_builders:
        return _parameter_code_builders[kernelspec.language](parameters)
    raise PapermillException(
        "No parameter builder functions specified for kernel '%s' or language '%s'"
        % (kernel_name, kernelspec.language))


def _find_parameters_index(nb):
    parameters_indices = []
    for idx, cell in enumerate(nb.cells):
        if "parameters" in cell.metadata.tags:
            parameters_indices.append(idx)
    if not parameters_indices:
        return -1
    elif len(parameters_indices) > 1:
        raise PapermillException("Multiple cells with parameters tag found")
    return parameters_indices[0]

def _translate_escaped_str(str_val):
    """Reusable by most interpreters"""
    if isinstance(str_val, string_types):
        str_val = str_val.encode('unicode_escape')
        if sys.version_info >= (3, 0):
            str_val = str_val.decode('utf-8')
        str_val = str_val.replace('"', r'\"')
    return '"{}"'.format(str_val)

def _translate_to_str(val):
    """Reusable by most interpreters"""
    return '{}'.format(val)

# Registry for functions that build parameter assignment code.
_parameter_code_builders = {}

# Python translaters
_translate_type_str_python = _translate_escaped_str
_translate_type_int_python = _translate_to_str
_translate_type_float_python = _translate_to_str
_translate_type_bool_python = _translate_to_str

def _translate_type_dict_python(val):
    escaped = ', '.join(["{}: {}".format(_translate_type_str_python(k), _translate_type_python(v)) for k, v in val.items()])
    return '{{{}}}'.format(escaped)

def _translate_type_list_python(val):
    escaped = ', '.join([_translate_type_python(v) for v in val])
    return '[{}]'.format(escaped)

def _translate_type_python(val):
    """Translate each of the standard json/yaml types to appropiate objects in python."""
    if isinstance(val, string_types):
        return _translate_type_str_python(val)
    # Needs to be before integer checks
    elif isinstance(val, bool):
        return _translate_type_bool_python(val)
    elif isinstance(val, integer_types):
        return _translate_type_int_python(val)
    elif isinstance(val, float):
        return _translate_type_float_python(val)
    elif isinstance(val, dict):
        return _translate_type_dict_python(val)
    elif isinstance(val, list):
        return _translate_type_list_python(val)
    # Use this generic translation as a last resort
    return _translate_escaped_str(val)

# R translaters
_translate_type_str_r = _translate_escaped_str
_translate_type_int_r = _translate_to_str
_translate_type_float_r = _translate_to_str

def _translate_type_bool_r(val):
    return 'TRUE' if val else 'FALSE'

def _translate_type_dict_r(val):
    escaped = ', '.join(["{} = {}".format(_translate_type_str_r(k), _translate_type_r(v)) for k, v in val.items()])
    return 'list({})'.format(escaped)

def _translate_type_list_r(val):
    escaped = ', '.join([_translate_type_r(v) for v in val])
    return 'list({})'.format(escaped)

def _translate_type_r(val):
    """Translate each of the standard json/yaml types to appropiate objects in R."""
    if isinstance(val, string_types):
        return _translate_type_str_r(val)
    # Needs to be before integer checks
    elif isinstance(val, bool):
        return _translate_type_bool_r(val)
    elif isinstance(val, integer_types):
        return _translate_type_int_r(val)
    elif isinstance(val, float):
        return _translate_type_float_r(val)
    elif isinstance(val, dict):
        return _translate_type_dict_r(val)
    elif isinstance(val, list):
        return _translate_type_list_r(val)
    # Use this generic translation as a last resort
    return _translate_escaped_str(val)

_translate_type_str_scala = _translate_escaped_str
_translate_type_int_scala = _translate_to_str
_translate_type_float_scala = _translate_to_str

def _translate_type_bool_scala(val):
    return 'true' if val else 'false'

def _translate_type_dict_scala(val):
    """Translate dicts to scala maps"""
    escaped = ', '.join(["{} -> {}".format(_translate_type_str_scala(k), _translate_type_scala(v)) 
                         for k, v in val.items()])
    return 'Map({})'.format(escaped)

def _translate_type_list_scala(val):
    """Translate list to scala Seq."""
    escaped = ', '.join([_translate_type_scala(v) for v in val])
    return 'Seq({})'.format(escaped)

def _translate_type_scala(val):
    """Translate each of the standard json/yaml types to appropiate objects in scala."""
    if isinstance(val, string_types):
        return _translate_type_str_scala(val)
    # Needs to be before integer checks
    elif isinstance(val, bool):
        return _translate_type_bool_scala(val)
    elif isinstance(val, integer_types):
        return _translate_type_int_scala(val)
    elif isinstance(val, float):
        return _translate_type_float_scala(val)
    elif isinstance(val, dict):
        return _translate_type_dict_scala(val)
    elif isinstance(val, list):
        return _translate_type_list_scala(val)
    # Use this generic translation as a last resort
    return _translate_escaped_str(val)

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
        param_content += '{} = {}\n'.format(var, _translate_type_python(val))
    return param_content


@register_param_builder("R")
def build_r_params(parameters):
    """Writes parameters assignment code for R kernels."""
    param_content = "# Parameters\n"
    for var, val in parameters.items():
        param_content += '{} = {}\n'.format(var, _translate_type_r(val))
    return param_content

@register_param_builder("scala")
def build_scala_params(parameters):
    """Writers parameter assignment code for Python kernels."""
    param_content = "// Parameters\n"
    for var, val in parameters.items():
        param_content += 'val {} = {}\n'.format(var, _translate_type_scala(val))
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
    '</span>')


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
                    traceback=output.traceback)
                break

    if error:
        # Write notebook back out with the Error Message at the top of the Notebook.
        error_msg = ERROR_MESSAGE_TEMPLATE % str(error.exec_count)
        error_msg_cell = nbformat.v4.new_code_cell(
            source="%%html\n" + error_msg,
            outputs=[
                nbformat.v4.new_output(
                    output_type="display_data",
                    data={"text/html": error_msg})
            ],
            metadata={"inputHidden": True,
                      "hide_input": True})
        nb.cells = [error_msg_cell] + nb.cells
        write_ipynb(nb, output_path)
        raise error
