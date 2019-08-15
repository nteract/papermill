# -*- coding: utf-8 -*-
"""Main `papermill` interface."""
from __future__ import unicode_literals

import os
import sys
from stat import S_ISFIFO

import base64
import logging

import click

import yaml
import platform

from .execute import execute_notebook
from .iorw import read_yaml_file, NoDatesSafeLoader
from . import __version__ as papermill_version

click.disable_unicode_literals_warning = True

INPUT_PIPED = S_ISFIFO(os.fstat(0).st_mode)
OUTPUT_PIPED = not sys.stdout.isatty()


def print_papermill_version(ctx, param, value):
    if not value:
        return
    print(
        "{version} from {path} ({pyver})".format(
            version=papermill_version, path=__file__, pyver=platform.python_version()
        )
    )
    ctx.exit()


class OptionEatAll(click.Option):
    # https://stackoverflow.com/a/48394004
    def __init__(self, *args, **kwargs):
        self.save_other_options = kwargs.pop('save_other_options', True)
        nargs = kwargs.pop('nargs', -1)
        assert nargs == -1, 'nargs, if set, must be -1 not {}'.format(nargs)
        super(OptionEatAll, self).__init__(*args, **kwargs)
        self._previous_parser_process = None
        self._eat_all_parser = None

    def add_to_parser(self, parser, ctx):

        def parser_process(value, state):
            # method to hook to the parser.process
            done = False
            value = [value]
            if self.save_other_options:
                # grab everything up to the next option
                while state.rargs and not done:
                    for prefix in self._eat_all_parser.prefixes:
                        if state.rargs[0].startswith(prefix):
                            done = True
                    if not done:
                        value.append(state.rargs.pop(0))
            else:
                # grab everything remaining
                value += state.rargs
                state.rargs[:] = []
            value = tuple(value)

            # call the actual process
            self._previous_parser_process(value, state)

        retval = super(OptionEatAll, self).add_to_parser(parser, ctx)
        for name in self.opts:
            our_parser = parser._long_opt.get(name) or parser._short_opt.get(name)
            if our_parser:
                self._eat_all_parser = our_parser
                self._previous_parser_process = our_parser.process
                our_parser.process = parser_process
                break
        return retval


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('notebook_path', required=not INPUT_PIPED)
@click.argument('output_path', required=not (INPUT_PIPED or OUTPUT_PIPED))
@click.option(
    '--parameters', '-p', multiple=True, help='Parameters to pass to the parameters cell.',
    cls=OptionEatAll,
)
@click.option(
    '--parameters_raw', '-r', multiple=True, help='Parameters to be read as raw string.',
    cls=OptionEatAll,
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
@click.option('--request-save-on-cell-execute', default=True,
              help='Request save notebook after each cell execution')
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
    request_save_on_cell_execute,
    prepare_only,
    kernel,
    cwd,
    progress_bar,
    log_output,
    log_level,
    start_timeout,
    report_mode,
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
    if INPUT_PIPED and notebook_path and not output_path:
        output_path = notebook_path
        notebook_path = '-'
    else:
        notebook_path = notebook_path or '-'
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
        parameters_final['PAPERMILL_INPUT_PATH'] = notebook_path
    if inject_output_path or inject_paths:
        parameters_final['PAPERMILL_OUTPUT_PATH'] = output_path
    for params in parameters_base64 or []:
        parameters_final.update(yaml.load(base64.b64decode(params), Loader=NoDatesSafeLoader))
    for files in parameters_file or []:
        parameters_final.update(read_yaml_file(files))
    for params in parameters_yaml or []:
        parameters_final.update(yaml.load(params, Loader=NoDatesSafeLoader))
    for name_values in parameters or []:
        name, values = name_values[0], name_values[1:]
        if not values:
            raise ValueError("There must be at least one value for key '{}'".format(name))
        values = [_resolve_type(v) for v in values]
        parameters_final[name] = values[0] if len(values) == 1 else values
    for name_values in parameters_raw or []:
        name, values = name_values[0], name_values[1:]
        if not values:
            raise ValueError("There must be at least one value for key '{}'".format(name))
        values = list(values)
        parameters_final[name] = values[0] if len(values) == 1 else values

    execute_notebook(
        notebook_path,
        output_path,
        parameters_final,
        engine_name=engine,
        request_save_on_cell_execute=request_save_on_cell_execute,
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
