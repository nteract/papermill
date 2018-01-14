# -*- coding: utf-8 -*-
"""Main `papermill` interface."""
from __future__ import unicode_literals

import base64

import click
import yaml

from .execute import execute_notebook
from .iorw import read_yaml_file


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('notebook_path')
@click.argument('output_path')
@click.option('--parameters', '-p', nargs=2, multiple=True,
              help='Parameters to pass to the parameters cell.')
@click.option('--parameters_raw', '-r', nargs=2, multiple=True,
              help='Parameters to be read as raw string.')
@click.option('--parameters_file', '-f',
              help='Path to YAML file containing parameters.')
@click.option('--parameters_yaml', '-y',
              help='YAML string to be used as parameters.')
@click.option('--parameters_base64', '-b',
              help='Base64 encoded YAML string as parameters.')
@click.option('--kernel', '-k', help='Name of kernel to run.')
@click.option('--progress-bar/--no-progress-bar', default=True,
              help="Flag for turning on the progress bar.")
@click.option('--log-output/--no-log-output', default=False,
              help="Flag for writing notebook output to stderr.")
def papermill(notebook_path, output_path, parameters, parameters_raw,
              parameters_file, parameters_yaml, parameters_base64, kernel,
              progress_bar, log_output):
    """This utility executes a single notebook on a container.

    Papermill takes a source notebook, applies parameters to the source
    notebook, executes the notebook with the specified kernel, and saves the
    output in the destination notebook.

    """
    if parameters_base64:
        parameters_final = yaml.load(base64.b64decode(parameters_base64))
    elif parameters_yaml:
        parameters_final = yaml.load(parameters_yaml)
    elif parameters_file:
        parameters_final = read_yaml_file(parameters_file)
    else:
        # Read in Parameters
        parameters_final = {}
        for name, value in parameters:
            parameters_final[name] = _resolve_type(value)
        for name, value in parameters_raw:
            parameters_final[name] = value

    execute_notebook(notebook_path, output_path, parameters_final,
                     kernel_name=kernel, progress_bar=progress_bar,
                     log_output=log_output)


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
