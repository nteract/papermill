import unittest

import six

from ..api import read_notebook
from ..execute import _parameterize_notebook
from . import get_notebook_path

PYTHON = 'python2' if six.PY2 else 'python3'


class TestNotebookParametrizing(unittest.TestCase):
    def count_nb_injected_parameter_cells(self, nb):
        return len(
            [c for c in nb.node.cells if 'injected-parameters' in c.get('metadata').get('tags', [])]
        )

    def test_no_tag_copying(self):
        # Test that injected cell does not copy other tags
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))
        test_nb.node.cells[0]['metadata']['tags'].append('some tag')

        _parameterize_notebook(test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = test_nb.node.cells[0]
        self.assertTrue('some tag' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters' in cell_zero.get('metadata').get('tags'))

        cell_one = test_nb.node.cells[1]
        self.assertTrue('some tag' not in cell_one.get('metadata').get('tags'))
        self.assertTrue('injected-parameters' in cell_one.get('metadata').get('tags'))

        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_injected_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))

        _parameterize_notebook(test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = test_nb.node.cells[0]
        self.assertTrue('parameters' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('injected-parameters' not in cell_zero.get('metadata').get('tags'))

        cell_one = test_nb.node.cells[1]
        self.assertTrue('injected-parameters' in cell_one.get('metadata').get('tags'))
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_repeated_run_injected_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 0)

        _parameterize_notebook(test_nb.node, PYTHON, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

        _parameterize_notebook(test_nb.node, PYTHON, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_no_parameter_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))
        test_nb.node.cells[0]['metadata']['tags'] = []

        _parameterize_notebook(test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = test_nb.node.cells[0]
        self.assertTrue('injected-parameters' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters' not in cell_zero.get('metadata').get('tags'))
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_repeated_run_no_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))
        test_nb.node.cells[0]['metadata']['tags'] = []
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 0)

        _parameterize_notebook(test_nb.node, PYTHON, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

        _parameterize_notebook(test_nb.node, PYTHON, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)
