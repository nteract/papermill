# -*- coding: utf-8 -*-
"""Main `papermill` interface."""
from __future__ import unicode_literals

import base64
import logging

import click

import yaml
import platform

from .execute import execute_notebook
from .iorw import read_yaml_file
from . import __version__ as papermill_version

click.disable_unicode_literals_warning = True


def print_papermill_version(ctx, param, value):
    if not value:
        return
    print(
        "{version} from {path} ({pyver})".format(
            version=papermill_version, path=__file__, pyver=platform.python_version()
        )
    )
    ctx.exit()


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('notebook_path')
@click.argument('output_path')
@click.option(
    '--parameters', '-p', nargs=2, multiple=True, help='Parameters to pass to the parameters cell.'
)
@click.option(
    '--parameters_raw', '-r', nargs=2, multiple=True, help='Parameters to be read as raw string.'
)
@click.option(
    '--parameters_file', '-f', multiple=True, help='Path to YAML file containing parameters.'
)
@click.option(
    '--parameters_yaml', '-y', multiple=True, help='YAML string to be used as parameters.'
)
@click.option(
    '--parameters_base64', '-b', multiple=True, help='Base64 encoded YAML string as parameters.'
)
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
    '--prepare-only/--prepare-execute',
    default=False,
    help="Flag for outputting the notebook without execution, but with parameters applied.",
)
@click.option('--kernel', '-k', help='Name of kernel to run.')
@click.option('--cwd', default=None, help='Working directory to run notebook in.')
@click.option(
    '--progress-bar/--no-progress-bar', default=None, help="Flag for turning on the progress bar."
)
@click.option(
    '--log-output/--no-log-output',
    default=False,
    help="Flag for writing notebook output to stderr.",
)
@click.option(
    '--log-level',
    type=click.Choice(['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    default='INFO',
    help='Set log level',
)
@click.option(
    '--start_timeout', type=int, default=60, help="Time in seconds to wait for kernel to start."
)
@click.option('--report-mode/--not-report-mode', default=False, help="Flag for hiding input.")
@click.option(
    '--version',
    is_flag=True,
    callback=print_papermill_version,
    expose_value=False,
    is_eager=True,
    help='Flag for displaying the version.',
)
def papermill(
    notebook_path,
    output_path,
    parameters,
    parameters_raw,
    parameters_file,
    parameters_yaml,
    parameters_base64,
    inject_input_path,
    inject_output_path,
    inject_paths,
    engine,
    prepare_only,
    kernel,
    cwd,
    progress_bar,
    log_output,
    log_level,
    start_timeout,
    report_mode,
):
    """This utility executes a single notebook on a container.

    Papermill takes a source notebook, applies parameters to the source
    notebook, executes the notebook with the specified kernel, and saves the
    output in the destination notebook.

    """
    logging.basicConfig(level=log_level, format="%(message)s")

    if progress_bar is None:
        progress_bar = not log_output

    # Read in Parameters
    parameters_final = {}
    if inject_input_path or inject_paths:
        parameters_final['PAPERMILL_INPUT_PATH'] = notebook_path
    if inject_output_path or inject_paths:
        parameters_final['PAPERMILL_OUTPUT_PATH'] = output_path
    for params in parameters_base64 or []:
        parameters_final.update(yaml.load(base64.b64decode(params)))
    for files in parameters_file or []:
        parameters_final.update(read_yaml_file(files))
    for params in parameters_yaml or []:
        parameters_final.update(yaml.load(params))
    for name, value in parameters or []:
        parameters_final[name] = _resolve_type(value)
    for name, value in parameters_raw or []:
        parameters_final[name] = value

    execute_notebook(
        notebook_path,
        output_path,
        parameters_final,
        engine_name=engine,
        prepare_only=prepare_only,
        kernel_name=kernel,
        progress_bar=progress_bar,
        log_output=log_output,
        start_timeout=start_timeout,
        report_mode=report_mode,
        cwd=cwd,
    )


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


if __name__ == '__main__':
    papermill()
