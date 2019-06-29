import unittest

from ..iorw import load_notebook_node
from ..exceptions import PapermillMissingParameterException
from ..parameterize import parameterize_notebook, parameterize_path, add_builtin_parameters
from . import get_notebook_path
from datetime import datetime


class TestNotebookParametrizing(unittest.TestCase):
    def count_nb_injected_parameter_cells(self, nb):
        return len(
            [c for c in nb.cells if 'injected-parameters' in c.get('metadata', {}).get('tags', [])]
        )

    def test_no_tag_copying(self):
        # Test that injected cell does not copy other tags
        test_nb = load_notebook_node(get_notebook_path("simple_execute.ipynb"))
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
        test_nb = load_notebook_node(get_notebook_path("simple_execute.ipynb"))

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})

        cell_zero = test_nb.cells[0]
        self.assertTrue('parameters' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('injected-parameters' not in cell_zero.get('metadata').get('tags'))

        cell_one = test_nb.cells[1]
        self.assertTrue('injected-parameters' in cell_one.get('metadata').get('tags'))
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_repeated_run_injected_parameters_tag(self):
        test_nb = load_notebook_node(get_notebook_path("simple_execute.ipynb"))
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 0)

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

        parameterize_notebook(test_nb, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_no_parameter_tag(self):
        test_nb = load_notebook_node(get_notebook_path("simple_execute.ipynb"))
        test_nb.cells[0]['metadata']['tags'] = []

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})

        cell_zero = test_nb.cells[0]
        self.assertTrue('injected-parameters' in cell_zero.get('metadata').get('tags'))
        self.assertTrue('parameters' not in cell_zero.get('metadata').get('tags'))
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

    def test_repeated_run_no_parameters_tag(self):
        test_nb = load_notebook_node(get_notebook_path("simple_execute.ipynb"))
        test_nb.cells[0]['metadata']['tags'] = []
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 0)

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)

        test_nb = parameterize_notebook(test_nb, {'msg': 'Hello'})
        self.assertEqual(self.count_nb_injected_parameter_cells(test_nb), 1)


class TestBuiltinParameters(unittest.TestCase):
    def test_add_builtin_parameters_keeps_provided_parameters(self):
        with_builtin_parameters = add_builtin_parameters({"foo": "bar"})
        self.assertEqual(with_builtin_parameters["foo"], "bar")

    def test_add_builtin_parameters_adds_dict_of_builtins(self):
        with_builtin_parameters = add_builtin_parameters({"foo": "bar"})
        self.assertIn("pm", with_builtin_parameters)
        self.assertIsInstance(with_builtin_parameters["pm"], type({}))

    def test_add_builtin_parameters_allows_to_override_builtin(self):
        with_builtin_parameters = add_builtin_parameters({"pm": "foo"})
        self.assertEqual(with_builtin_parameters["pm"], "foo")

    def test_builtin_parameters_include_run_uuid(self):
        with_builtin_parameters = add_builtin_parameters({"foo": "bar"})
        self.assertIn("run_uuid", with_builtin_parameters["pm"])

    def test_builtin_parameters_include_current_datetime_local(self):
        with_builtin_parameters = add_builtin_parameters({"foo": "bar"})
        self.assertIn("current_datetime_local", with_builtin_parameters["pm"])
        self.assertIsInstance(with_builtin_parameters["pm"]["current_datetime_local"], datetime)

    def test_builtin_parameters_include_current_datetime_utc(self):
        with_builtin_parameters = add_builtin_parameters({"foo": "bar"})
        self.assertIn("current_datetime_utc", with_builtin_parameters["pm"])
        self.assertIsInstance(with_builtin_parameters["pm"]["current_datetime_utc"], datetime)


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

    def test_path_with_dict_parameter(self):
        self.assertEqual(
            parameterize_path("foo/{bar[baz]}/", {"bar": {"baz": "quux"}}), "foo/quux/"
        )

    def test_path_with_list_parameter(self):
        self.assertEqual(parameterize_path("foo/{bar[0]}/", {"bar": [1, 2, 3]}), "foo/1/")
        self.assertEqual(parameterize_path("foo/{bar[2]}/", {"bar": [1, 2, 3]}), "foo/3/")

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
        with self.assertRaises(PapermillMissingParameterException) as context:
            parameterize_path("{foo}", {})
        self.assertEqual(str(context.exception), "Missing parameter 'foo'")

    def test_parameterized_path_with_none_parameters(self):
        with self.assertRaises(PapermillMissingParameterException) as context:
            parameterize_path("{foo}", None)
        self.assertEqual(str(context.exception), "Missing parameter 'foo'")
