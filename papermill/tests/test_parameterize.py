import unittest

from ..api import read_notebook
from ..execute import _parameterize_notebook
from . import get_notebook_path


class TestNotebookHelpers(unittest.TestCase):
    def test_preserving_tags(self):
        # test that other tags on the parameter cell are preserved
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))
        test_nb.node.cells[0]['metadata']['tags'].append('some tag')

        _parameterize_notebook(test_nb.node, 'python3', {'msg': 'Hello'})

        cell_zero = test_nb.node.cells[0]
        self.assertTrue('some tag' in cell_zero.get('metadata').get('tags'))

        cell_one = test_nb.node.cells[1]
        self.assertTrue('some tag' in cell_one.get('metadata').get('tags'))
        self.assertTrue('parameters' in cell_one.get('metadata').get('tags'))

    def test_default_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))
        test_nb.node.cells[0]['metadata']['tags'].append('some tag')

        _parameterize_notebook(test_nb.node, 'python3', {'msg': 'Hello'})

        cell_zero = test_nb.node.cells[0]
        self.assertTrue('default parameters'
                        in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        not in cell_zero.get('metadata').get('tags'))
