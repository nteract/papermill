# -*- coding: utf-8 -*-
"""Main `papermill` interface."""
from __future__ import unicode_literals

import base64

import click
click.disable_unicode_literals_warning = True

import yaml

from functools import wraps
from .execute import execute_notebook
from .iorw import read_yaml_file

def add_options(options):
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func
    return _add_options

_options = [
    click.option('--parameters', '-p', nargs=2, multiple=True,
                  help='Parameters to pass to the parameters cell.'),
    click.option('--parameters_raw', '-r', nargs=2, multiple=True,
                  help='Parameters to be read as raw string.'),
    click.option('--parameters_file', '-f', multiple=True,
                  help='Path to YAML file containing parameters.'),
    click.option('--parameters_yaml', '-y', multiple=True,
                  help='YAML string to be used as parameters.'),
    click.option('--parameters_base64', '-b', multiple=True,
                  help='Base64 encoded YAML string as parameters.'),
    click.option('--prepare-only/--prepare-execute', default=False,
                  help="Flag for outputting the notebook without execution, "
                       "but with parameters applied."),
    click.option('--kernel', '-k', help='Name of kernel to run.'),
    click.option('--progress-bar/--no-progress-bar', default=True,
                  help="Flag for turning on the progress bar."),
    click.option('--log-output/--no-log-output', default=False,
                  help="Flag for writing notebook output to stderr."),
    click.option('--start_timeout', type=int, default=60,
                  help="Time in seconds to wait for kernel to start."),
    click.option('--report-mode/--not-report-mode', default=False,
                  help="Flag for hiding input."),
]

@click.command()
@click.argument('notebook_path')
@click.option('--help/--no-help', '-h', default=True)
@add_options(_options)
def notebook_help(notebook_path, help, **kwarg):
    '''
    We make a separate function here with --help available to enable
    the same automatic error messaging, but with the ability to hijack
    the normal help messaging for when a user types `--help` on an
    input notebook
    '''
    # TODO add inspection function here!
    click.echo("notebook_path: {}".format(notebook_path))

class NotebookCommand(click.Command):
    @property
    def arguments(self):
        for param in self.params:
            if isinstance(param, click.core.Argument):
                yield param

    def arg_count(self):
        return len(list(arg for arg in self.arguments))

    def maybe_input_help(self):
        # We want the normal help message if we don't have --help (arg 2)
        return self.arg_count() == 2

    def get_help(self, ctx):
        """Formats the help into a string and returns it.  This creates a
        formatter and will call into the following formatting methods:
        """
        if (self.maybe_input_help()):
            return notebook_help()
        return super(NotebookCommand, self).get_help(ctx)

    def format_usage(self, ctx, formatter):
        """Writes the usage line into the formatter."""
        pieces = ['[OUTPUT_PATH/--help/-h]' if p == 'OUTPUT_PATH' else p
                  for p in self.collect_usage_pieces(ctx)]
        formatter.write_usage(ctx.command_path, ' '.join(pieces))

@click.command(cls=NotebookCommand,
               context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('notebook_path')
@click.argument('output_path')
@add_options(_options)
def papermill(notebook_path, output_path, parameters, parameters_raw,
              parameters_file, parameters_yaml, parameters_base64, prepare_only,
              kernel, progress_bar, log_output, start_timeout, report_mode):
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

    execute_notebook(notebook_path, output_path, parameters_final,
                     prepare_only=prepare_only,
                     kernel_name=kernel,
                     progress_bar=progress_bar,
                     log_output=log_output,
                     start_timeout=start_timeout,
                     report_mode=report_mode)

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
