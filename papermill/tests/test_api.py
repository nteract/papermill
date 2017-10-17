import pytest
import unittest

import pandas as pd
from pandas.util.testing import assert_frame_equal

from papermill import read_notebook, read_notebooks, PapermillException
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
            columns=['name', 'value', 'type', 'filename']
        )
        assert_frame_equal(nb.dataframe, expected_df)

    def test_bad_file_ext(self):

        with self.assertRaises(PapermillException):
            read_notebook('result_notebook.py')


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
                ('dict', {u'a': 1, u'b': 2}, 'record','result2.ipynb', 'result2.ipynb'),
                ('list', [1, 2, 3], 'record', 'result2.ipynb', 'result2.ipynb'),
                ('number', 1, 'record', 'result2.ipynb', 'result2.ipynb'),
            ],
            columns=['name', 'value', 'type', 'filename', 'key']
        )
        assert_frame_equal(nbs.dataframe, expected_df)

        expected_metrics_df = pd.DataFrame(
            [
                ('result1.ipynb', 'Out [1]', 0.0, 'time (s)', 'result1.ipynb'),
                ('result1.ipynb', 'Out [2]', 0.0, 'time (s)', 'result1.ipynb'),
                ('result2.ipynb', 'Out [1]', 0.0, 'time (s)', 'result2.ipynb'),
                ('result2.ipynb', 'Out [2]', 0.0, 'time (s)', 'result2.ipynb'),

            ],
            columns=['filename', 'cell', 'value', 'type', 'key']
        )
        assert_frame_equal(nbs.metrics, expected_metrics_df)
