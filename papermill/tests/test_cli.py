#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

""" Test the command line interface """

import os
import unittest

from mock import patch

from .. import cli
from ..cli import papermill, _is_int,  _is_float, _resolve_type, execute_notebook
from click.testing import CliRunner

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.default_args = ['input.ipynb', 'output.ipynb']
        self.sample_yaml_file = os.path.join(os.path.dirname(__file__), 'parameters', 'example.yaml')
        self.sample_json_file = os.path.join(os.path.dirname(__file__), 'parameters', 'example.json')

    def test_resolve_types(self):
        in_out_pairs = [
            ("True", True),
            ("False", False),
            ("None", None),
            ("12.51", 12.51),
            ("10", 10),
            ("hello world", "hello world"),
            ("😍", "😍"),
        ]
        for tin, tout in in_out_pairs:
            self.assertEqual(_resolve_type(tin), tout)

    def test_is_float(self):
        in_out_pairs = [
            (13.71, True),
            ("False", False),
            ("None", False),
            (-8.2, True),
            (10, True),
            ("10", True),
            ("12.31", True),
            ("hello world", False),
            ("😍", False),
        ]
        for tin, tout in in_out_pairs:
            self.assertEqual(_is_float(tin), tout)

    def test_is_int(self):
        in_out_pairs = [
            (13.71, True),
            ("False", False),
            ("None", False),
            (-8.2, True),
            ("-23.2", False),
            (10, True),
            ("13", True),
            ("hello world", False),
            ("😍", False),
        ]
        for tin, tout in in_out_pairs:
            self.assertEqual(_is_int(tin), tout)

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['-p', 'foo', 'bar', '--parameters', 'baz', '42'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'foo': 'bar', 'baz': 42},
            kernel_name=None,
            log_output=False,
            progress_bar=True)

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_raw(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['-r', 'foo', 'bar', '--parameters_raw', 'baz', '42'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'foo': 'bar', 'baz': '42'},
            kernel_name=None,
            log_output=False,
            progress_bar=True)

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_file(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['-f', self.sample_yaml_file, '--parameters_file', self.sample_json_file])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            # Last input wins dict update
            {'foo': 54321, 'bar': 'value', 'baz': {'k2': 'v2', 'k1': 'v1'}},
            kernel_name=None,
            log_output=False,
            progress_bar=True)

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_yaml(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['-y', '{"foo": "bar"}', '--parameters_yaml', '{"foo2": ["baz"]}'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'foo': 'bar', 'foo2': ['baz']},
            kernel_name=None,
            log_output=False,
            progress_bar=True)

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_yaml_override(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--parameters_yaml', '{"foo": "bar"}', '-y', '{"foo": ["baz"]}'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            # Last input wins dict update
            {'foo': ['baz']},
            kernel_name=None,
            log_output=False,
            progress_bar=True)

    @patch(cli.__name__ + '.execute_notebook')
    def test_parameters_base64(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--parameters_base64', 'eyJmb28iOiAicmVwbGFjZWQiLCAiYmFyIjogMn0=', '-b', 'eydmb28nOiAxfQ=='])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            # Last input wins dict update
            {'foo': 1, 'bar': 2},
            kernel_name=None,
            log_output=False,
            progress_bar=True)

    @patch(cli.__name__ + '.execute_notebook')
    def test_kernel(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['-k', 'python3'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            kernel_name='python3',
            log_output=False,
            progress_bar=True)

    @patch(cli.__name__ + '.execute_notebook')
    def test_progress_bar(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--progress-bar'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            kernel_name=None,
            log_output=False,
            progress_bar=True)

    @patch(cli.__name__ + '.execute_notebook')
    def test_no_progress_bar(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--no-progress-bar'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            kernel_name=None,
            log_output=False,
            progress_bar=False)

    @patch(cli.__name__ + '.execute_notebook')
    def test_log_output(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--log-output'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            kernel_name=None,
            log_output=True,
            progress_bar=True)

    @patch(cli.__name__ + '.execute_notebook')
    def test_log_output(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + ['--no-log-output'])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {},
            kernel_name=None,
            log_output=False,
            progress_bar=True)

    @patch(cli.__name__ + '.execute_notebook')
    def test_many_args(self, execute_patch):
        self.runner.invoke(papermill, self.default_args + [
            '-f', self.sample_yaml_file,
            '-y', '{"yaml_foo": {"yaml_bar": "yaml_baz"}}',
            '-b', 'eyJiYXNlNjRfZm9vIjogImJhc2U2NF9iYXIifQ==',
            '-p', 'baz', 'replace',
            '-r', 'foo', '54321',
            '--kernel', 'R',
            '--log-output',
            '--no-progress-bar'
        ])
        execute_patch.assert_called_with(
            'input.ipynb',
            'output.ipynb',
            {'foo': '54321', 'bar': 'value', 'baz': 'replace', 'yaml_foo': {'yaml_bar': 'yaml_baz'}, "base64_foo": "base64_bar"},
            kernel_name='R',
            log_output=True,
            progress_bar=False)
