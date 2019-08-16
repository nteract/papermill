#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Test the command line interface """

import os
import sys
import subprocess
import nbformat
from jupyter_client import kernelspec
import unittest

import pytest
import click
from click.testing import CliRunner

from mock import patch

from .. import cli
from ..cli import papermill, _is_int, _is_float, _resolve_type


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("True", True),
        ("False", False),
        ("None", None),
        ("12.51", 12.51),
        ("10", 10),
        ("hello world", "hello world"),
        (u"😍", u"😍"),
    ],
)
def test_resolve_type(test_input, expected):
    assert _resolve_type(test_input) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (13.71, True),
        ("False", False),
        ("None", False),
        (-8.2, True),
        (10, True),
        ("10", True),
        ("12.31", True),
        ("hello world", False),
        (u"😍", False),
    ],
)
def test_is_float(value, expected):
    assert (_is_float(value)) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (13.71, True),
        ("False", False),
        ("None", False),
        (-8.2, True),
        ("-23.2", False),
        (10, True),
        ("13", True),
        ("hello world", False),
        (u"😍", False),
    ],
)
def test_is_int(value, expected):
    assert (_is_int(value)) == expected


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.default_args = ['input.ipynb', 'output.ipynb']
        self.sample_yaml_file = os.path.join(
            os.path.dirname(__file__), 'parameters', 'example.yaml'
        )
        self.sample_json_file = os.path.join(
            os.path.dirname(__file__), 'parameters', 'example.json'
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters(self, execute_patch):
        self.runner.invoke(
            papermill, self.default_args + ['-p', 'foo', 'bar', '--parameters', 'baz', '42']
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'foo': 'bar', 'baz': 42},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_list_args(self, execute_patch):
        self.runner.invoke(
            papermill, self.default_args + ['-p', 'foo', 'bar', 'baz', '0',
                                            '-p', 'one', 'two',
                                            '--parameters', 'qux', '42']
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'foo': ['bar', 'baz', 0], 'one': 'two', 'qux': 42},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_raw(self, execute_patch):
        self.runner.invoke(
            papermill, self.default_args + ['-r', 'foo', 'bar', '--parameters_raw', 'baz', '42']
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'foo': 'bar', 'baz': '42'},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_raw_list_args(self, execute_patch):
        self.runner.invoke(
            papermill, self.default_args + ['-r', 'foo', 'bar', 'baz', '0',
                                            '-r', 'one', 'two',
                                            '--parameters_raw', 'qux', '42']
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'foo': ['bar', 'baz', '0'], 'one': 'two', 'qux': '42'},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_file(self, execute_patch):
        self.runner.invoke(
            papermill,
            self.default_args
            + ['-f', self.sample_yaml_file, '--parameters_file', self.sample_json_file],
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            # Last input wins dict update
            {'foo': 54321, 'bar': 'value', 'baz': {'k2': 'v2', 'k1': 'v1'}, 'a_date': '2019-01-01'},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_yaml(self, execute_patch):
        self.runner.invoke(
            papermill,
            self.default_args + ['-y', '{"foo": "bar"}', '--parameters_yaml', '{"foo2": ["baz"]}'],
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'foo': 'bar', 'foo2': ['baz']},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_yaml_date(self, execute_patch):
        self.runner.invoke(
            papermill,
            self.default_args + ['-y', 'a_date: 2019-01-01'],
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'a_date': '2019-01-01'},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_yaml_override(self, execute_patch):
        self.runner.invoke(
            papermill,
            self.default_args + ['--parameters_yaml', '{"foo": "bar"}', '-y', '{"foo": ["baz"]}'],
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            # Last input wins dict update
            {'foo': ['baz']},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_base64(self, execute_patch):
        self.runner.invoke(
            papermill,
            self.default_args
            + [
                '--parameters_base64',
                'eyJmb28iOiAicmVwbGFjZWQiLCAiYmFyIjogMn0=',
                '-b',
                'eydmb28nOiAxfQ==',
            ],
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            # Last input wins dict update
            {'foo': 1, 'bar': 2},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_base64_date(self, execute_patch):
        self.runner.invoke(
            papermill,
            self.default_args
            + [
                '--parameters_base64',
                'YV9kYXRlOiAyMDE5LTAxLTAx',
            ],
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'a_date': '2019-01-01'},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_inject_input_path(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--inject-input-path'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            # Last input wins dict update
            {'PAPERMILL_INPUT_PATH': 'input.ipynb'},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_inject_output_path(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--inject-output-path'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            # Last input wins dict update
            {'PAPERMILL_OUTPUT_PATH': 'output.ipynb'},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_inject_paths(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--inject-paths'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            # Last input wins dict update
            {'PAPERMILL_INPUT_PATH': 'input.ipynb', 'PAPERMILL_OUTPUT_PATH': 'output.ipynb'},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_engine(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--engine', 'engine-that-could'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name='engine-that-could',
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_prepare_only(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--prepare-only'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=True,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_kernel(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['-k', 'python3'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name='python3',
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_set_cwd(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--cwd', 'a/path/here'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd='a/path/here',
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_progress_bar(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--progress-bar'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_no_progress_bar(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--no-progress-bar'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=False,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_log_output(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--log-output'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=True,
            progress_bar=False,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_log_output_plus_progress(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--log-output', '--progress-bar'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=True,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_no_log_output(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--no-log-output'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_log_level(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--log-level', 'WARNING'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_start_timeout(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--start_timeout', '123'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=123,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_report_mode(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--report-mode'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=True,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_no_report_mode(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--not-report-mode'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            engine_name=None,
            request_save_on_cell_execute=True,
            prepare_only=False,
            kernel_name=None,
            log_output=False,
            progress_bar=True,
            start_timeout=60,
            report_mode=False,
            cwd=None,
        )

    @patch(cli.__name__ + '.execute_notebook')
    def test_version(self, execute_patch):
        self.runner.invoke(papermill, ['--version'])
        execute_patch.assert_not_called()

    @patch(cli.__name__ + '.execute_notebook')
    def test_many_args(self, execute_patch):
        self.runner.invoke(
            papermill,
            self.default_args
            + [
                '-f',
                self.sample_yaml_file,
                '-y',
                '{"yaml_foo": {"yaml_bar": "yaml_baz"}}',
                '-b',
                'eyJiYXNlNjRfZm9vIjogImJhc2U2NF9iYXIifQ==',
                '-p',
                'baz',
                'replace',
                '-r',
                'foo',
                '54321',
                '--kernel',
                'R',
                '--engine',
                'engine-that-could',
                '--prepare-only',
                '--log-output',
                '--no-progress-bar',
                '--start_timeout',
                '321',
                '--report-mode',
            ],
        )
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {
                'foo': '54321',
                'bar': 'value',
                'baz': 'replace',
                'yaml_foo': {'yaml_bar': 'yaml_baz'},
                "base64_foo": "base64_bar",
                'a_date': '2019-01-01',
            },
            engine_name='engine-that-could',
            request_save_on_cell_execute=True,
            prepare_only=True,
            kernel_name='R',
            log_output=True,
            progress_bar=False,
            start_timeout=321,
            report_mode=True,
            cwd=None,
        )


def test_cli_path():
    @click.command()
    @click.argument('notebook_path')
    @click.argument('output_path')
    def cli(notebook_path, output_path):
        click.echo('papermill calling %s and %s!' % notebook_path, output_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            'papermill',
            'notebooks/s3/s3_in/s3-simple_notebook.ipynb',
            'notebooks/s3/s3_out/output.ipynb',
        ],
    )
    assert result.output


def test_papermill_log():
    @click.group()
    @click.option('--log-output/--no-output', default=False)
    def cli(log_output):
        click.echo('Log output mode is %s' % ('on' if log_output else 'off'))

    @cli.command()
    def papermill():
        click.echo('Logging')

    runner = CliRunner()
    result = runner.invoke(cli, ['--log-output', 'papermill'])
    assert result.exit_code == 0
    assert 'Log output mode is on' in result.output
    assert 'Logging' in result.output


def papermill_cli(papermill_args=None, **kwargs):
    cmd = [sys.executable, '-m', 'papermill.cli']
    if papermill_args:
        cmd.extend(papermill_args)
    return subprocess.Popen(cmd, **kwargs)


def papermill_version():
    try:
        proc = papermill_cli(['--version'], stdout=subprocess.PIPE)
        out, _ = proc.communicate()
        if proc.returncode:
            return None
        return out.decode('utf-8')
    except (OSError, SystemExit):  # pragma: no cover
        return None


@pytest.fixture()
def notebook():
    for name in kernelspec.find_kernel_specs():
        ks = kernelspec.get_kernel_spec(name)
        metadata = {'kernelspec': {'name': name,
                                   'language': ks.language,
                                   'display_name': ks.display_name}}
        return nbformat.v4.new_notebook(
            metadata=metadata,
            cells=[nbformat.v4.new_markdown_cell(
                'This is a notebook with kernel: ' + ks.display_name)])

    raise EnvironmentError('No kernel found')


require_papermill_installed = pytest.mark.skipif(
    not papermill_version(),
    reason='papermill is not installed')


@require_papermill_installed
def test_pipe_in_out_auto(notebook):
    process = papermill_cli(stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    text = nbformat.writes(notebook)
    out, err = process.communicate(input=text.encode('utf-8'))

    # Test no message on std error
    assert not err

    # Test that output is a valid notebook
    nbformat.reads(out.decode('utf-8'), as_version=4)


@require_papermill_installed
def test_pipe_in_out_explicit(notebook):
    process = papermill_cli(['-', '-'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    text = nbformat.writes(notebook)
    out, err = process.communicate(input=text.encode('utf-8'))

    # Test no message on std error
    assert not err

    # Test that output is a valid notebook
    nbformat.reads(out.decode('utf-8'), as_version=4)


@require_papermill_installed
def test_pipe_out_auto(tmpdir, notebook):
    nb_file = tmpdir.join('notebook.ipynb')
    nb_file.write(nbformat.writes(notebook))

    process = papermill_cli([str(nb_file)], stdout=subprocess.PIPE)
    out, err = process.communicate()

    # Test no message on std error
    assert not err

    # Test that output is a valid notebook
    nbformat.reads(out.decode('utf-8'), as_version=4)


@require_papermill_installed
def test_pipe_out_explicit(tmpdir, notebook):
    nb_file = tmpdir.join('notebook.ipynb')
    nb_file.write(nbformat.writes(notebook))

    process = papermill_cli([str(nb_file), '-'], stdout=subprocess.PIPE)
    out, err = process.communicate()

    # Test no message on std error
    assert not err

    # Test that output is a valid notebook
    nbformat.reads(out.decode('utf-8'), as_version=4)


@require_papermill_installed
def test_pipe_in_auto(tmpdir, notebook):
    nb_file = tmpdir.join('notebook.ipynb')

    process = papermill_cli([str(nb_file)], stdin=subprocess.PIPE)
    text = nbformat.writes(notebook)
    out, _ = process.communicate(input=text.encode('utf-8'))

    # Nothing on stdout
    assert not out

    # Test that output is a valid notebook
    with open(str(nb_file)) as fp:
        nbformat.reads(fp.read(), as_version=4)


@require_papermill_installed
def test_pipe_in_explicit(tmpdir, notebook):
    nb_file = tmpdir.join('notebook.ipynb')

    process = papermill_cli(['-', str(nb_file)], stdin=subprocess.PIPE)
    text = nbformat.writes(notebook)
    out, _ = process.communicate(input=text.encode('utf-8'))

    # Nothing on stdout
    assert not out

    # Test that output is a valid notebook
    with open(str(nb_file)) as fp:
        nbformat.reads(fp.read(), as_version=4)
