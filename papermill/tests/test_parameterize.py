import unittest

from ..api import read_notebook
from ..execute import parameterize_notebook, parameterize_path
from . import get_notebook_path


class TestNotebookParametrizing(unittest.TestCase):
    def count_nb_injected_parameter_cells(self, nb):
        return len(
            [c for c in nb.cells if 'injected-parameters' in c.get('metadata', {}).get('tags', [])]
        )

    def test_no_tag_copying(self):
        # Test that injected cell does not copy other tags
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb")).node
        test_nb.cells[0]['metadata']['tags'].append('some tag')

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})

        cell_zero = test_nb.cells[0]
        self.assertTrue('some tag' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters' in cell_zero.get('metadata').get('tags'))

        cell_one = test_nb.cells[1]
        self.assertTrue('some tag' not in cell_one.get('metadata').get('tags'))
        self.assertTrue('injected-parameters' in cell_one.get('metadata').get('tags'))

        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_injected_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb")).node

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})

        cell_zero = test_nb.cells[0]
        self.assertTrue('parameters' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('injected-parameters' not in cell_zero.get('metadata').get('tags'))

        cell_one = test_nb.cells[1]
        self.assertTrue('injected-parameters' in cell_one.get('metadata').get('tags'))
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_repeated_run_injected_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb")).node
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 0)

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

        parameterize_notebook(test_nb, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_no_parameter_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb")).node
        test_nb.cells[0]['metadata']['tags'] = []

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})

        cell_zero = test_nb.cells[0]
        self.assertTrue('injected-parameters' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters' not in cell_zero.get('metadata').get('tags'))
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_repeated_run_no_parameters_tag(self):
        test_nb = read_notebook(get_notebook_path("simple_execute.ipynb")).node
        test_nb.cells[0]['metadata']['tags'] = []
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 0)

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)


class TestPathParameterizing(unittest.TestCase):
    def test_plain_text_path_with_empty_parameters_object(self):
        self.assertEqual(parameterize_path("foo/bar", {}), "foo/bar")

    def test_plain_text_path_with_none_parameters(self):
        self.assertEqual(parameterize_path("foo/bar", None), "foo/bar")

    def test_plain_text_path_with_unused_parameters(self):
        self.assertEqual(parameterize_path("foo/bar", {"baz": "quux"}), "foo/bar")

    def test_path_with_single_parameter(self):
        self.assertEqual(parameterize_path("foo/bar/{baz}", {"baz": "quux"}), "foo/bar/quux")

    def test_path_with_boolean_parameter(self):
        self.assertEqual(parameterize_path("foo/bar/{baz}", {"baz": False}), "foo/bar/False")

    def test_path_with_none_parameter(self):
        self.assertEqual(parameterize_path("foo/bar/{baz}", {"baz": None}), "foo/bar/None")

    def test_path_with_numeric_parameter(self):
        self.assertEqual(parameterize_path("foo/bar/{baz}", {"baz": 42}), "foo/bar/42")

    def test_path_with_numeric_format_string(self):
        self.assertEqual(parameterize_path("foo/bar/{baz:03d}", {"baz": 42}), "foo/bar/042")

    def test_path_with_float_format_string(self):
        self.assertEqual(parameterize_path("foo/bar/{baz:.03f}", {"baz": 0.3}), "foo/bar/0.300")

    def test_path_with_multiple_parameter(self):
        self.assertEqual(
            parameterize_path("{foo}/{baz}", {"foo": "bar", "baz": "quux"}), "bar/quux"
        )

    def test_parameterized_path_with_undefined_parameter(self):
        with self.assertRaises(Exception) as context:
            parameterize_path("{foo}", {})
        self.assertEqual(str(context.exception), "Missing parameters: foo")

    def test_parameterized_path_with_undefined_parameters(self):
        with self.assertRaises(Exception) as context:
            parameterize_path("{foo} {bar} {foo}", {})
        self.assertEqual(str(context.exception), "Missing parameters: foo, bar")

    def test_parameterized_path_with_none_parameters(self):
        with self.assertRaises(Exception) as context:
            parameterize_path("{foo} {bar} {foo}", None)
        self.assertEqual(str(context.exception), "Missing parameters: foo, bar")
