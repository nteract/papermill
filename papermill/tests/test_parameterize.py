import unittest

import six

from ..api import read_notebook
from ..execute import _parameterize_notebook
from . import get_notebook_path

PYTHON = 'python2' if six.PY2 else 'python3'


class TestNotebookParametrizing(unittest.TestCase):
    def test_not_preserving_tags(self):
        # test that other tags on the parameter cell are _not_ preserved
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))
        test_nb.node.cells[0]['metadata']['tags'].append('some tag')

        _parameterize_notebook(test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = test_nb.node.cells[0]
        self.assertTrue('some tag' in cell_zero.get('metadata').get('tags'))

        cell_one = test_nb.node.cells[1]
        self.assertTrue('some tag' not in cell_one.get('metadata').get('tags'))
        self.assertTrue('parameters' in cell_one.get('metadata').get('tags'))

    def test_default_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))

        _parameterize_notebook(test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = test_nb.node.cells[0]
        self.assertTrue('default parameters'
                        in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        not in cell_zero.get('metadata').get('tags'))

    def test_no_parameters(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))
        test_nb.node.cells[0]['metadata']['tags'].append('some tag')

        _parameterize_notebook(test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = test_nb.node.cells[0]
        self.assertTrue('default parameters'
                        in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        not in cell_zero.get('metadata').get('tags'))
