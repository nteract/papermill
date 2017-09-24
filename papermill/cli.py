# -*- coding: utf-8 -*-

"""Main `papermill` interface."""

import base64
import click
import yaml
from papermill.execute import execute_notebook
from papermill.iorw import read_yaml_file


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('src')
@click.argument('dst')
@click.option(
    '--param', '-p',
    help='Parameters to pass to the parameters cell.',
    multiple=True, nargs=2
)
@click.option(
    '--raw_param', '-r',
    help='Parameters to be read as raw string.',
    multiple=True, nargs=2
)
@click.option(
    '--file_param', '-f',
    help='Path to YAML file containing parameters.'
)
@click.option(
    '--yaml_param', '-y',
    help='YAML string to be used as parameters.'
)
@click.option(
    '--base64_param', '-b',
    help='Base64 encoded YAML string as parameters.'
)
@click.option(
    '--kernel', '-k',
    help='Name of kernel to run.'
)
def papermill(
             src, dst,
             param, raw_param,
             file_param, yaml_param, base64_param,
             kernel):
    """Utility for executing a single notebook on a container."""
    if base64_param:
        param_final = yaml.load(base64.b64decode(base64_param))
    elif yaml_param:
        param_final = yaml.load(yaml_param)
    elif file_param:
        param_final = read_yaml_file(file_param)
    else:
        # Read in Parameters
        param_final = {}
        for name, value in param:
            param_final[name] = _resolve_type(value)
        for name, value in raw_param:
            param_final[name] = value

    execute_notebook(src, dst, param_final, kernel_name=kernel)


def _resolve_type(value):
    if value == "True":
        return True
    elif value == "False":
        return False
    elif value == "None":
        return None
    elif _is_float(value):
        return float(value)
    elif _is_int(value):
        return int(value)
    else:
        return value


def _is_int(value):
    try:
        int(value)
    except ValueError:
        return False
    return True


def _is_float(value):
    try:
        float(value)
    except ValueError:
        return False
    return "." in value


if __name__ == '__main__':
    papermill()
