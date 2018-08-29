# -*- coding: utf-8 -*-
"""Main `papermill` interface."""
from __future__ import unicode_literals

import base64

import click

import yaml

from .execute import execute_notebook
from .iorw import read_yaml_file

click.disable_unicode_literals_warning = True


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
    '--prepare-only/--prepare-execute',
    default=False,
    help="Flag for outputting the notebook without execution, " "but with parameters applied.",
)
@click.option('--kernel', '-k', help='Name of kernel to run.')
@click.option(
    '--progress-bar/--no-progress-bar', default=True, help="Flag for turning on the progress bar."
)
@click.option(
    '--log-output/--no-log-output',
    default=False,
    help="Flag for writing notebook output to stderr.",
)
@click.option(
    '--start_timeout', type=int, default=60, help="Time in seconds to wait for kernel to start."
)
@click.option('--report-mode/--not-report-mode', default=False, help="Flag for hiding input.")
def papermill(
    notebook_path,
    output_path,
    parameters,
    parameters_raw,
    parameters_file,
    parameters_yaml,
    parameters_base64,
    prepare_only,
    kernel,
    progress_bar,
    log_output,
    start_timeout,
    report_mode,
):
    """This utility executes a single notebook on a container.

    Papermill takes a source notebook, applies parameters to the source
    notebook, executes the notebook with the specified kernel, and saves the
    output in the destination notebook.

    """
    # Read in Parameters
    parameters_final = {}
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
        prepare_only=prepare_only,
        kernel_name=kernel,
        progress_bar=progress_bar,
        log_output=log_output,
        start_timeout=start_timeout,
        report_mode=report_mode,
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
