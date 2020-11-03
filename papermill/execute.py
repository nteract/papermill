# -*- coding: utf-8 -*-

import copy
import nbformat
from pathlib import Path

from .log import logger
from .exceptions import PapermillExecutionError
from .iorw import get_pretty_path, local_file_io_cwd, load_notebook_node, write_ipynb
from .engines import papermill_engines
from .utils import chdir
from .parameterize import add_builtin_parameters, parameterize_notebook, parameterize_path


def execute_notebook(
    input_path,
    output_path,
    parameters=None,
    engine_name=None,
    request_save_on_cell_execute=True,
    prepare_only=False,
    kernel_name=None,
    progress_bar=True,
    log_output=False,
    stdout_file=None,
    stderr_file=None,
    start_timeout=60,
    report_mode=False,
    cwd=None,
    **engine_kwargs
):
    """Executes a single notebook locally.

    Parameters
    ----------
    input_path : str or Path
        Path to input notebook
    output_path : str or Path
        Path to save executed notebook
    parameters : dict, optional
        Arbitrary keyword arguments to pass to the notebook parameters
    engine_name : str, optional
        Name of execution engine to use
    request_save_on_cell_execute : bool, optional
        Request save notebook after each cell execution
    autosave_cell_every : int, optional
        How often in seconds to save in the middle of long cell executions
    prepare_only : bool, optional
        Flag to determine if execution should occur or not
    kernel_name : str, optional
        Name of kernel to execute the notebook against
    progress_bar : bool, optional
        Flag for whether or not to show the progress bar.
    log_output : bool, optional
        Flag for whether or not to write notebook output to the configured logger
    start_timeout : int, optional
        Duration in seconds to wait for kernel start-up
    report_mode : bool, optional
        Flag for whether or not to hide input.
    cwd : str or Path, optional
        Working directory to use when executing the notebook
    **kwargs
        Arbitrary keyword arguments to pass to the notebook engine

    Returns
    -------
    nb : NotebookNode
       Executed notebook object
    """
    if isinstance(input_path, Path):
        input_path = str(input_path)
    if isinstance(output_path, Path):
        output_path = str(output_path)
    if isinstance(cwd, Path):
        cwd = str(cwd)

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
        # clear out any existing error markers from previous papermill runs
        nb = remove_error_markers(nb)

        if not prepare_only:
            # Fetch the kernel name if it's not supplied
            kernel_name = kernel_name or nb.metadata.kernelspec.name

            # Execute the Notebook in `cwd` if it is set
            with chdir(cwd):
                nb = papermill_engines.execute_notebook_with_engine(
                    engine_name,
                    nb,
                    input_path=input_path,
                    output_path=output_path if request_save_on_cell_execute else None,
                    kernel_name=kernel_name,
                    progress_bar=progress_bar,
                    log_output=log_output,
                    start_timeout=start_timeout,
                    stdout_file=stdout_file,
                    stderr_file=stderr_file,
                    **engine_kwargs
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


ERROR_MARKER_TAG = "papermill-error-cell-tag"

ERROR_STYLE = (
    'style="color:red; font-family:Helvetica Neue, Helvetica, Arial, sans-serif; font-size:2em;"'
)

ERROR_MESSAGE_TEMPLATE = (
    '<span ' + ERROR_STYLE + '>'
    "An Exception was encountered at '<a href=\"#papermill-error-cell\">In [%s]</a>'."
    '</span>'
)

ERROR_ANCHOR_MSG = (
    '<span id="papermill-error-cell" ' + ERROR_STYLE + '>'
    'Execution using papermill encountered an exception here and stopped:'
    '</span>'
)


def remove_error_markers(nb):
    nb = copy.deepcopy(nb)
    nb.cells = [
        cell
        for cell in nb.cells
        if ERROR_MARKER_TAG not in cell.metadata.get("tags", [])
    ]
    return nb


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
    for index, cell in enumerate(nb.cells):
        if cell.get("outputs") is None:
            continue

        for output in cell.outputs:
            if output.output_type == "error":
                if output.ename == "SystemExit" and (output.evalue == "" or output.evalue == "0"):
                    continue
                error = PapermillExecutionError(
                    cell_index=index,
                    exec_count=cell.execution_count,
                    source=cell.source,
                    ename=output.ename,
                    evalue=output.evalue,
                    traceback=output.traceback,
                )
                break

    if error:
        # Write notebook back out with the Error Message at the top of the Notebook, and a link to
        # the relevant cell (by adding a note just before the failure with an HTML anchor)
        error_msg = ERROR_MESSAGE_TEMPLATE % str(error.exec_count)
        error_msg_cell = nbformat.v4.new_markdown_cell(error_msg)
        error_msg_cell.metadata['tags'] = [ERROR_MARKER_TAG]
        error_anchor_cell = nbformat.v4.new_markdown_cell(ERROR_ANCHOR_MSG)
        error_anchor_cell.metadata['tags'] = [ERROR_MARKER_TAG]

        # put the anchor before the cell with the error, before all the indices change due to the
        # heading-prepending
        nb.cells.insert(error.cell_index, error_anchor_cell)
        nb.cells.insert(0, error_msg_cell)

        write_ipynb(nb, output_path)
        raise error
