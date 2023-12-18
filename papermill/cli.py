"""Main `papermill` interface."""

import base64
import logging
import os
import platform
import sys
import traceback
from stat import S_ISFIFO

import click
import nbclient
import yaml

from .execute import execute_notebook
from .inspection import display_notebook_help
from .iorw import NoDatesSafeLoader, read_yaml_file
from .version import version as papermill_version

click.disable_unicode_literals_warning = True

INPUT_PIPED = S_ISFIFO(os.fstat(0).st_mode)
OUTPUT_PIPED = not sys.stdout.isatty()


def print_papermill_version(ctx, param, value):
    if not value:
        return
    print(f"{papermill_version} from {__file__} ({platform.python_version()})")
    ctx.exit()


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.pass_context
@click.argument('notebook_path', required=not INPUT_PIPED)
@click.argument('output_path', default="")
@click.option(
    '--help-notebook',
    is_flag=True,
    default=False,
    help='Display parameters information for the given notebook path.',
)
@click.option('--parameters', '-p', nargs=2, multiple=True, help='Parameters to pass to the parameters cell.')
@click.option('--parameters_raw', '-r', nargs=2, multiple=True, help='Parameters to be read as raw string.')
@click.option('--parameters_file', '-f', multiple=True, help='Path to YAML file containing parameters.')
@click.option('--parameters_yaml', '-y', multiple=True, help='YAML string to be used as parameters.')
@click.option('--parameters_base64', '-b', multiple=True, help='Base64 encoded YAML string as parameters.')
@click.option(
    '--inject-input-path',
    is_flag=True,
    default=False,
    help="Insert the path of the input notebook as PAPERMILL_INPUT_PATH as a notebook parameter.",
)
@click.option(
    '--inject-output-path',
    is_flag=True,
    default=False,
    help="Insert the path of the output notebook as PAPERMILL_OUTPUT_PATH as a notebook parameter.",
)
@click.option(
    '--inject-paths',
    is_flag=True,
    default=False,
    help=(
        "Insert the paths of input/output notebooks as PAPERMILL_INPUT_PATH/PAPERMILL_OUTPUT_PATH"
        " as notebook parameters."
    ),
)
@click.option('--engine', help='The execution engine name to use in evaluating the notebook.')
@click.option(
    '--request-save-on-cell-execute/--no-request-save-on-cell-execute',
    default=True,
    help='Request save notebook after each cell execution',
)
@click.option(
    '--autosave-cell-every',
    default=30,
    type=int,
    help='How often in seconds to autosave the notebook during long cell executions (0 to disable)',
)
@click.option(
    '--prepare-only/--prepare-execute',
    default=False,
    help="Flag for outputting the notebook without execution, but with parameters applied.",
)
@click.option(
    '--kernel',
    '-k',
    help='Name of kernel to run. Ignores kernel name in the notebook document metadata.',
)
@click.option(
    '--language',
    '-l',
    help='Language for notebook execution. Ignores language in the notebook document metadata.',
)
@click.option('--cwd', default=None, help='Working directory to run notebook in.')
@click.option('--progress-bar/--no-progress-bar', default=None, help="Flag for turning on the progress bar.")
@click.option(
    '--log-output/--no-log-output',
    default=False,
    help="Flag for writing notebook output to the configured logger.",
)
@click.option(
    '--stdout-file',
    type=click.File(mode='w', encoding='utf-8'),
    help="File to write notebook stdout output to.",
)
@click.option(
    '--stderr-file',
    type=click.File(mode='w', encoding='utf-8'),
    help="File to write notebook stderr output to.",
)
@click.option(
    '--log-level',
    type=click.Choice(['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    default='INFO',
    help='Set log level',
)
@click.option(
    '--start-timeout',
    '--start_timeout',  # Backwards compatible naming
    type=int,
    default=60,
    help="Time in seconds to wait for kernel to start.",
)
@click.option(
    '--execution-timeout',
    type=int,
    help="Time in seconds to wait for each cell before failing execution (default: forever)",
)
@click.option('--report-mode/--no-report-mode', default=False, help="Flag for hiding input.")
@click.option(
    '--version',
    is_flag=True,
    callback=print_papermill_version,
    expose_value=False,
    is_eager=True,
    help='Flag for displaying the version.',
)
def papermill(
    click_ctx,
    notebook_path,
    output_path,
    help_notebook,
    parameters,
    parameters_raw,
    parameters_file,
    parameters_yaml,
    parameters_base64,
    inject_input_path,
    inject_output_path,
    inject_paths,
    engine,
    request_save_on_cell_execute,
    autosave_cell_every,
    prepare_only,
    kernel,
    language,
    cwd,
    progress_bar,
    log_output,
    log_level,
    start_timeout,
    execution_timeout,
    report_mode,
    stdout_file,
    stderr_file,
):
    """This utility executes a single notebook in a subprocess.

    Papermill takes a source notebook, applies parameters to the source
    notebook, executes the notebook with the specified kernel, and saves the
    output in the destination notebook.

    The NOTEBOOK_PATH and OUTPUT_PATH can now be replaced by `-` representing
    stdout and stderr, or by the presence of pipe inputs / outputs.
    Meaning that

    `<generate input>... | papermill | ...<process output>`

    with `papermill - -` being implied by the pipes will read a notebook
    from stdin and write it out to stdout.

    """
    # Jupyter deps use frozen modules, so we disable the python 3.11+ warning about debugger if running the CLI
    if 'PYDEVD_DISABLE_FILE_VALIDATION' not in os.environ:
        os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

    if not help_notebook:
        required_output_path = not (INPUT_PIPED or OUTPUT_PIPED)
        if required_output_path and not output_path:
            raise click.UsageError("Missing argument 'OUTPUT_PATH'")

    if INPUT_PIPED and notebook_path and not output_path:
        input_path = '-'
        output_path = notebook_path
    else:
        input_path = notebook_path or '-'
        output_path = output_path or '-'

    if output_path == '-':
        # Save notebook to stdout just once
        request_save_on_cell_execute = False

        # Reduce default log level if we pipe to stdout
        if log_level == 'INFO':
            log_level = 'ERROR'

    elif progress_bar is None:
        progress_bar = not log_output

    logging.basicConfig(level=log_level, format="%(message)s")

    # Read in Parameters
    parameters_final = {}
    if inject_input_path or inject_paths:
        parameters_final['PAPERMILL_INPUT_PATH'] = input_path
    if inject_output_path or inject_paths:
        parameters_final['PAPERMILL_OUTPUT_PATH'] = output_path
    for params in parameters_base64 or []:
        parameters_final.update(yaml.load(base64.b64decode(params), Loader=NoDatesSafeLoader) or {})
    for files in parameters_file or []:
        parameters_final.update(read_yaml_file(files) or {})
    for params in parameters_yaml or []:
        parameters_final.update(yaml.load(params, Loader=NoDatesSafeLoader) or {})
    for name, value in parameters or []:
        parameters_final[name] = _resolve_type(value)
    for name, value in parameters_raw or []:
        parameters_final[name] = value

    if help_notebook:
        sys.exit(display_notebook_help(click_ctx, notebook_path, parameters_final))

    try:
        execute_notebook(
            input_path=input_path,
            output_path=output_path,
            parameters=parameters_final,
            engine_name=engine,
            request_save_on_cell_execute=request_save_on_cell_execute,
            autosave_cell_every=autosave_cell_every,
            prepare_only=prepare_only,
            kernel_name=kernel,
            language=language,
            progress_bar=progress_bar,
            log_output=log_output,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            start_timeout=start_timeout,
            report_mode=report_mode,
            cwd=cwd,
            execution_timeout=execution_timeout,
        )
    except nbclient.exceptions.DeadKernelError:
        # Exiting with a special exit code for dead kernels
        traceback.print_exc()
        sys.exit(138)


def _resolve_type(value):
    if value == "True":
        return True
    elif value == "False":
        return False
    elif value == "None":
        return None
    elif _is_int(value):
        return int(value)
    elif _is_float(value):
        return float(value)
    else:
        return value


def _is_int(value):
    """Use casting to check if value can convert to an `int`."""
    try:
        int(value)
    except ValueError:
        return False
    else:
        return True


def _is_float(value):
    """Use casting to check if value can convert to a `float`."""
    try:
        float(value)
    except ValueError:
        return False
    else:
        return True
