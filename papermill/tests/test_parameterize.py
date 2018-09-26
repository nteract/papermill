import unittest

import six

from ..api import read_notebook
from ..execute import parameterize_notebook
from . import get_notebook_path

PYTHON = 'python2' if six.PY2 else 'python3'


class TestNotebookParametrizing(unittest.TestCase):
    def count_nb_injected_parameter_cells(self, nb):
        return len(
            [c for c in nb.cells if 'injected-parameters' in c.get('metadata', {}).get('tags', [])]
        )

    def test_no_tag_copying(self):
        # Test that injected cell does not copy other tags
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb")).node
        test_nb.cells[0]['metadata']['tags'].append('some tag')

        test_nb = parameterize_notebook(test_nb, PYTHON, {'msg': 'Hello'})

        cell_zero = test_nb.cells[0]
        self.assertTrue('some tag' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters' in cell_zero.get('metadata').get('tags'))

        cell_one = test_nb.cells[1]
        self.assertTrue('some tag' not in cell_one.get('metadata').get('tags'))
        self.assertTrue('injected-parameters' in cell_one.get('metadata').get('tags'))

        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_injected_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb")).node

        test_nb = parameterize_notebook(test_nb, PYTHON, {'msg': 'Hello'})

        cell_zero = test_nb.cells[0]
        self.assertTrue('parameters' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('injected-parameters' not in cell_zero.get('metadata').get('tags'))

        cell_one = test_nb.cells[1]
        self.assertTrue('injected-parameters' in cell_one.get('metadata').get('tags'))
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_repeated_run_injected_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb")).node
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 0)

        test_nb = parameterize_notebook(test_nb, PYTHON, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

        parameterize_notebook(test_nb, PYTHON, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_no_parameter_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb")).node
        test_nb.cells[0]['metadata']['tags'] = []

        test_nb = parameterize_notebook(test_nb, PYTHON, {'msg': 'Hello'})

        cell_zero = test_nb.cells[0]
        self.assertTrue('injected-parameters' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters' not in cell_zero.get('metadata').get('tags'))
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_repeated_run_no_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb")).node
        test_nb.cells[0]['metadata']['tags'] = []
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 0)

        test_nb = parameterize_notebook(test_nb, PYTHON, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

        test_nb = parameterize_notebook(test_nb, PYTHON, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)
