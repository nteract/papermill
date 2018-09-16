# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import datetime
import os
import sys
import six
import nbformat

from .conf import settings
from .exceptions import PapermillExecutionError
from .preprocess import PapermillExecutePreprocessor
from .iorw import load_notebook_node, write_ipynb, read_yaml_file, get_pretty_path
from .translators import translate_parameters


def execute_notebook(
    notebook,
    output,
    parameters=None,
    prepare_only=False,
    kernel_name=None,
    progress_bar=True,
    log_output=False,
    start_timeout=60,
    report_mode=False,
):
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
        report_mode (bool): Flag for whether or not to hide input.

    Returns:
         nb (NotebookNode): Executed notebook object
    """
    print("Input Notebook:  %s" % get_pretty_path(notebook), file=sys.stderr)
    print("Output Notebook: %s" % get_pretty_path(output), file=sys.stderr)
    nb = load_notebook_node(notebook)

    # Parameterize the Notebook.
    if parameters:
        _parameterize_notebook(nb, kernel_name, parameters)

    # Hide input if report-mode is set to True.
    if report_mode:
        for cell in nb.cells:
            if cell.cell_type == 'code':
                cell.metadata['jupyter'] = cell.get('jupyter', {})
                cell.metadata['jupyter']['source_hidden'] = True

    # Record specified environment variable values.
    nb.metadata.papermill['environment_variables'] = _fetch_environment_variables()
    nb.metadata.papermill['output_path'] = output

    if not prepare_only:
        # Execute the Notebook.
        _execute_parameterized_notebook(nb, kernel_name, progress_bar, log_output, start_timeout)

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
    if isinstance(parameters, six.string_types):
        parameters = read_yaml_file(parameters)

    # Generate parameter content based on the kernal_name
    kernel_name = kernel_name or nb.metadata.kernelspec.name
    param_content = translate_parameters(kernel_name, parameters)

    newcell = nbformat.v4.new_code_cell(source=param_content)
    newcell.metadata['tags'] = ['injected-parameters']

    param_cell_index = _find_first_tagged_cell_index(nb, 'parameters')
    injected_cell_index = _find_first_tagged_cell_index(nb, 'injected-parameters')
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
        before = []
        after = nb.cells

    nb.cells = before + [newcell] + after
    nb.metadata.papermill['parameters'] = parameters


def _execute_parameterized_notebook(
    nb, kernel_name=None, progress_bar=True, log_output=False, start_timeout=60
):
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
        kernel_name=kernel_name or nb.metadata.kernelspec.name,
    )
    processor.progress_bar = progress_bar
    processor.log_output = log_output

    processor.preprocess(nb, {})
    t1 = datetime.datetime.utcnow()

    nb.metadata.papermill['start_time'] = t0.isoformat()
    nb.metadata.papermill['end_time'] = t1.isoformat()
    nb.metadata.papermill['duration'] = (t1 - t0).total_seconds()
    nb.metadata.papermill['exception'] = any(
        [cell.metadata.papermill.get('exception') for cell in nb.cells]
    )


def _find_first_tagged_cell_index(nb, tag):
    parameters_indices = []
    for idx, cell in enumerate(nb.cells):
        if tag in cell.metadata.tags:
            parameters_indices.append(idx)
    if not parameters_indices:
        return -1
    return parameters_indices[0]


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
                    traceback=output.traceback,
                )
                break

    if error:
        # Write notebook back out with the Error Message at the top of the Notebook.
        error_msg = ERROR_MESSAGE_TEMPLATE % str(error.exec_count)
        error_msg_cell = nbformat.v4.new_code_cell(
            source="%%html\n" + error_msg,
            outputs=[
                nbformat.v4.new_output(output_type="display_data", data={"text/html": error_msg})
            ],
            metadata={"inputHidden": True, "hide_input": True},
        )
        nb.cells = [error_msg_cell] + nb.cells
        write_ipynb(nb, output_path)
        raise error
