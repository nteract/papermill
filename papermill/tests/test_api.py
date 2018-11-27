import unittest
import pytest

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

import pandas as pd
from pandas.util.testing import assert_frame_equal

from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell, new_output

from .. import display, read_notebook, read_notebooks, PapermillException, record
from ..api import Notebook, _get_notebook_outputs
from . import get_notebook_path, get_notebook_dir


class TestNotebookClass(unittest.TestCase):
    def test(self):

        path = get_notebook_path('collection/result1.ipynb')
        nb = read_notebook(path)
        self.assertEqual(nb.version, '0.4+2.ge10f94c.dirty')
        self.assertEqual(nb.environment_variables, {})
        self.assertEqual(nb.parameters, dict(foo=1, bar="hello"))
        self.assertEqual(nb.directory, get_notebook_dir('collection/result1.ipynb'))
        expected_df = pd.DataFrame(
            [
                ('bar', 'hello', 'parameter', 'result1.ipynb'),
                ('foo', 1, 'parameter', 'result1.ipynb'),
                ('dict', {u'a': 1, u'b': 2}, 'record', 'result1.ipynb'),
                ('list', [1, 2, 3], 'record', 'result1.ipynb'),
                ('number', 1, 'record', 'result1.ipynb'),
            ],
            columns=['name', 'value', 'type', 'filename'],
        )
        assert_frame_equal(nb.dataframe, expected_df)

        with pytest.raises(PapermillException) as excinfo:
            nb.display_output('foo')
        assert "Output Name 'foo' is not available in this notebook." in str(excinfo.value)

    def test_bad_file_ext(self):

        with self.assertRaises(PapermillException):
            read_notebook('result_notebook.py')

    def test_path_without_node(self):

        with self.assertRaises(ValueError):
            Notebook(node=None, path='collection/result1.ipynb')

    def test_malformed_execution_count(self):
        path = get_notebook_path('result_no_exec.ipynb')
        nb = read_notebook(path)
        expected_df = pd.DataFrame(
            [],
            columns=['filename', 'cell', 'value', 'type'],
        )
        assert_frame_equal(nb.metrics, expected_df)


class TestNotebookCollection(unittest.TestCase):
    def test(self):

        path = get_notebook_path('collection')
        nbs = read_notebooks(path)

        expected_df = pd.DataFrame(
            [
                ('bar', 'hello', 'parameter', 'result1.ipynb', 'result1.ipynb'),
                ('foo', 1, 'parameter', 'result1.ipynb', 'result1.ipynb'),
                ('dict', {u'a': 1, u'b': 2}, 'record', 'result1.ipynb', 'result1.ipynb'),
                ('list', [1, 2, 3], 'record', 'result1.ipynb', 'result1.ipynb'),
                ('number', 1, 'record', 'result1.ipynb', 'result1.ipynb'),
                ('bar', 'world', 'parameter', 'result2.ipynb', 'result2.ipynb'),
                ('foo', 2, 'parameter', 'result2.ipynb', 'result2.ipynb'),
                ('dict', {u'a': 1, u'b': 2}, 'record', 'result2.ipynb', 'result2.ipynb'),
                ('list', [1, 2, 3], 'record', 'result2.ipynb', 'result2.ipynb'),
                ('number', 1, 'record', 'result2.ipynb', 'result2.ipynb'),
            ],
            columns=['name', 'value', 'type', 'filename', 'key'],
        )
        assert_frame_equal(nbs.dataframe, expected_df)

        expected_metrics_df = pd.DataFrame(
            [
                ('result1.ipynb', 'Out [1]', 0.0, 'time (s)', 'result1.ipynb'),
                ('result1.ipynb', 'Out [2]', 0.0, 'time (s)', 'result1.ipynb'),
                ('result2.ipynb', 'Out [1]', 0.0, 'time (s)', 'result2.ipynb'),
                ('result2.ipynb', 'Out [2]', 0.0, 'time (s)', 'result2.ipynb'),
            ],
            columns=['filename', 'cell', 'value', 'type', 'key'],
        )
        assert_frame_equal(nbs.metrics, expected_metrics_df)


class TestNotebookOutputs(unittest.TestCase):
    def test_get_notebook_outputs(self):
        output = new_output(
            output_type='display_data', data={}, metadata={'papermill': {'name': 'test'}}
        )
        nb = new_notebook(cells=[new_code_cell('test', outputs=[output])])
        assert _get_notebook_outputs(nb) == {'test': output}

    def test_notebook_no_cells(self):
        nb = new_notebook(cells=[])
        assert _get_notebook_outputs(nb) == {}

    def test_cell_with_no_outputs(self):
        nb = new_notebook(cells=[new_code_cell('test', outputs=[])])
        assert _get_notebook_outputs(nb) == {}

    def test_empty_metadata(self):
        output = new_output(output_type='display_data', data={}, metadata={})
        nb = new_notebook(cells=[new_code_cell('test', outputs=[output])])
        assert _get_notebook_outputs(nb) == {}

    def test_not_papermill_with_name(self):
        output = new_output(
            output_type='display_data', data={}, metadata={'not_papermill': {'name': 'test'}}
        )
        nb = new_notebook(cells=[new_code_cell('test', outputs=[output])])
        assert _get_notebook_outputs(nb) == {}

    def test_papermill_metadata_not_name(self):
        output = new_output(
            output_type='display_data', metadata={'papermill': {'not_name': 'test'}}
        )
        nb = new_notebook(cells=[new_code_cell('test', outputs=[output])])
        assert _get_notebook_outputs(nb) == {}

    def test_papermill_metadata_but_empty(self):
        output = new_output(output_type='display_data', metadata={'papermill': {}})
        nb = new_notebook(cells=[new_code_cell('test', outputs=[output])])
        assert _get_notebook_outputs(nb) == {}

    def test_no_outputs_with_markdown(self):
        nb = new_notebook(cells=[new_markdown_cell('this is a test.')])
        assert _get_notebook_outputs(nb) == {}


@patch('papermill.api.ip_display')
@patch('IPython.core.formatters.format_display_data')
def test_display(format_display_data_mock, ip_display_mock):
    format_display_data_mock.return_value = ({'foo': 'bar'}, {'metadata': 'baz'})
    display('display_name', {'display_obj': 'hello'})

    format_display_data_mock.assert_called_once_with({'display_obj': 'hello'})
    ip_display_mock.assert_called_once_with(
        {'foo': 'bar'},
        metadata={'metadata': 'baz', 'papermill': {'name': 'display_name'}},
        raw=True,
    )


@patch('papermill.api.ip_display')
def test_record(ip_display_mock):
    record('a', 3)
    ip_display_mock.assert_called_once_with(
        {'application/papermill.record+json': {'a': 3}}, raw=True
    )
