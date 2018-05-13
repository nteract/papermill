import unittest

import six

from ..api import read_notebook
from ..execute import _parameterize_notebook
from ..exceptions import PapermillException
from . import get_notebook_path

PYTHON = 'python2' if six.PY2 else 'python3'


class TestNotebookParametrizing(unittest.TestCase):
    def setUp(self):
        self.test_nb = read_notebook(get_notebook_path("simple_execute.ipynb"))

    def test_not_preserving_tags(self):
        # test that other tags on the parameter cell are _not_ preserved
        self.test_nb.node.cells[0]['metadata']['tags'].append('some tag')

        _parameterize_notebook(self.test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = self.test_nb.node.cells[0]
        self.assertTrue('some tag' in cell_zero.get('metadata').get('tags'))

        cell_one = self.test_nb.node.cells[1]
        self.assertTrue('some tag' not in cell_one.get('metadata').get('tags'))
        self.assertTrue('parameters' in cell_one.get('metadata').get('tags'))

    def test_default_parameters_tag(self):
        _parameterize_notebook(self.test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = self.test_nb.node.cells[0]
        self.assertTrue('default parameters'
                        in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        not in cell_zero.get('metadata').get('tags'))

    def test_no_parameters(self):
        self.test_nb.node.cells[0]['metadata']['tags'].append('some tag')

        _parameterize_notebook(self.test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = self.test_nb.node.cells[0]
        self.assertTrue('default parameters'
                        in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        not in cell_zero.get('metadata').get('tags'))


    def test_parameterize_repeated(self):
        _parameterize_notebook(self.test_nb.node, PYTHON, {'msg': 'Hello'})
        _parameterize_notebook(self.test_nb.node, PYTHON, {'msg': 'Hello 2'})

        self.assertEqual(
            self.test_nb.node.metadata.papermill.parameters,
            {'msg': 'Hello 2'})

        cell_zero = self.test_nb.node.cells[0]
        self.assertTrue('default parameters'
                        in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        not in cell_zero.get('metadata').get('tags'))

        cell_one = self.test_nb.node.cells[1]
        self.assertTrue('default parameters'
                        not in cell_one.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        in cell_one.get('metadata').get('tags'))
        self.assertEqual(
            cell_one.get('source').split('\n'),
            ['# Parameters', 'msg = "Hello 2"', ''])

    def test_parameters_in_metadata_with_tag(self):
        self.test_nb.node.metadata.papermill['parameters'] = {'msg': 'Hello -1'}
        _parameterize_notebook(self.test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = self.test_nb.node.cells[0]
        self.assertTrue('default parameters'
                        not in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        in cell_zero.get('metadata').get('tags'))
        self.assertEqual(
            cell_zero.get('source').split('\n'),
            ['# Parameters', 'msg = "Hello"', ''])

        cell_one = self.test_nb.node.cells[1]
        self.assertTrue('default parameters'
                        not in cell_one.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        not in cell_one.get('metadata').get('tags'))

    def test_parameters_metadata_with_param_cell(self):
        self.test_nb.node.metadata.papermill['parameters'] = {'msg': 'Hello -1'}
        self.test_nb.node.metadata.papermill['parameter_cell'] = 0
        _parameterize_notebook(self.test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = self.test_nb.node.cells[0]
        self.assertTrue('default parameters'
                        not in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        in cell_zero.get('metadata').get('tags'))
        self.assertEqual(
            cell_zero.get('source').split('\n'),
            ['# Parameters', 'msg = "Hello"', ''])

        cell_one = self.test_nb.node.cells[1]
        self.assertTrue('default parameters'
                        not in cell_one.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        not in cell_one.get('metadata').get('tags'))

    def test_parameters_metadata_with_param_cell_mismatch(self):
        self.test_nb.node.metadata.papermill['parameters'] = {'msg': 'Hello -1'}
        self.test_nb.node.metadata.papermill['parameter_cell'] = 1
        _parameterize_notebook(self.test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = self.test_nb.node.cells[0]
        self.assertTrue('default parameters'
                        in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        not in cell_zero.get('metadata').get('tags'))

        cell_one = self.test_nb.node.cells[1]
        self.assertTrue('default parameters'
                        not in cell_one.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        in cell_one.get('metadata').get('tags'))
        self.assertEqual(
            cell_one.get('source').split('\n'),
            ['# Parameters', 'msg = "Hello"', ''])

    def test_parameters_in_metadata_but_no_tag(self):
        self.test_nb = read_notebook(get_notebook_path("no_parameters.ipynb"))
        self.test_nb.node.metadata.papermill['parameters'] = {'msg': 'Hello -1'}
        _parameterize_notebook(self.test_nb.node, PYTHON, {'msg': 'Hello'})

        cell_zero = self.test_nb.node.cells[0]
        self.assertTrue('default parameters'
                        not in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        in cell_zero.get('metadata').get('tags'))
        self.assertEqual(
            cell_zero.get('source').split('\n'),
            ['# Parameters', 'msg = "Hello"', ''])

        cell_one = self.test_nb.node.cells[1]
        self.assertTrue('default parameters'
                        not in cell_one.get('metadata').get('tags'))
        self.assertTrue('parameters'
                        not in cell_one.get('metadata').get('tags'))

    def test_fails_with_duplicate_parameter_tags(self):
        self.test_nb.node.cells[0]['metadata']['tags'].append('parameters')
        self.test_nb.node.cells[1]['metadata']['tags'].append('parameters')

        self.assertRaises(PapermillException,
            lambda: _parameterize_notebook(self.test_nb.node, PYTHON, {'msg': 'Hello'}))
