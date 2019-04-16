# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import copy
import nbformat

from .log import logger
from .exceptions import PapermillExecutionError
from .iorw import load_notebook_node, write_ipynb, get_pretty_path, local_file_io_cwd
from .engines import papermill_engines
from .utils import chdir
from .parameterize import parameterize_notebook, parameterize_path, add_builtin_parameters


def execute_notebook(
    input_path,
    output_path,
    parameters=None,
    engine_name=None,
    prepare_only=False,
    kernel_name=None,
    progress_bar=True,
    log_output=False,
    start_timeout=60,
    report_mode=False,
    cwd=None,
):
    """Executes a single notebook locally.

    Parameters
    ----------
    input_path : str
        Path to input notebook
    output_path : str
        Path to save executed notebook
    parameters : dict, optional
        Arbitrary keyword arguments to pass to the notebook parameters
    engine_name : str, optional
        Name of execution engine to use
    prepare_only : bool, optional
        Flag to determine if execution should occur or not
    kernel_name : str, optional
        Name of kernel to execute the notebook against
    progress_bar : bool, optional
        Flag for whether or not to show the progress bar.
    log_output : bool, optional
        Flag for whether or not to write notebook output_path to `stderr`
    start_timeout : int, optional
        Duration in seconds to wait for kernel start-up
    report_mode : bool, optional
        Flag for whether or not to hide input.
    cwd : str, optional
        Working directory to use when executing the notebook

    Returns
    -------
    nb : NotebookNode
       Executed notebook object
    """
    path_parameters = add_builtin_parameters(parameters)
    input_path = parameterize_path(input_path, path_parameters)
    output_path = parameterize_path(output_path, path_parameters)

    logger.info("Input Notebook:  %s" % get_pretty_path(input_path))
    logger.info("Output Notebook: %s" % get_pretty_path(output_path))
    with local_file_io_cwd():
        if cwd is not None:
            logger.info("Working directory: {}".format(get_pretty_path(cwd)))

        nb = load_notebook_node(input_path)

        # Parameterize the Notebook.
        if parameters:
            nb = parameterize_notebook(nb, parameters, report_mode)

        nb = prepare_notebook_metadata(nb, input_path, output_path, report_mode)

        if not prepare_only:
            # Fetch the kernel name if it's not supplied
            kernel_name = kernel_name or nb.metadata.kernelspec.name

            # Execute the Notebook in `cwd` if it is set
            with chdir(cwd):
                nb = papermill_engines.execute_notebook_with_engine(
                    engine_name,
                    nb,
                    input_path=input_path,
                    output_path=output_path,
                    kernel_name=kernel_name,
                    progress_bar=progress_bar,
                    log_output=log_output,
                    start_timeout=start_timeout,
                )

            # Check for errors first (it saves on error before raising)
            raise_for_execution_errors(nb, output_path)

        # Write final output in case the engine didn't write it on cell completion.
        write_ipynb(nb, output_path)

        return nb


def prepare_notebook_metadata(nb, input_path, output_path, report_mode=False):
    """Prepare metadata associated with a notebook and its cells

    Parameters
    ----------
    nb : NotebookNode
       Executable notebook object
    input_path : str
        Path to input notebook
    output_path : str
       Path to write executed notebook
    report_mode : bool, optional
       Flag to set report mode
    """
    # Copy the nb object to avoid polluting the input
    nb = copy.deepcopy(nb)

    # Hide input if report-mode is set to True.
    if report_mode:
        for cell in nb.cells:
            if cell.cell_type == 'code':
                cell.metadata['jupyter'] = cell.get('jupyter', {})
                cell.metadata['jupyter']['source_hidden'] = True

    # Record specified environment variable values.
    nb.metadata.papermill['input_path'] = input_path
    nb.metadata.papermill['output_path'] = output_path

    return nb


ERROR_MESSAGE_TEMPLATE = (
    '<span style="color:red; font-family:Helvetica Neue, Helvetica, Arial, sans-serif; font-size:2em;">'
    "An Exception was encountered at 'In [%s]'."
    '</span>'
)


def raise_for_execution_errors(nb, output_path):
    """Assigned parameters into the appropriate place in the input notebook

    Parameters
    ----------
    nb : NotebookNode
       Executable notebook object
    output_path : str
       Path to write executed notebook
    """
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
