import os
import io
import six
import shutil
import tempfile
import unittest

from functools import partial

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from nbconvert import HTMLExporter

from .. import engines
from ..log import logger
from ..iorw import load_notebook_node
from ..utils import chdir
from ..execute import execute_notebook
from ..exceptions import PapermillExecutionError
from . import get_notebook_path


if six.PY2:
    kernel_name = 'python2'
else:
    kernel_name = 'python3'
execute_notebook = partial(execute_notebook, kernel_name=kernel_name)


class TestNotebookHelpers(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.notebook_name = 'simple_execute.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb_test_executed_fname = os.path.join(
            self.test_dir, 'output_{}'.format(self.notebook_name)
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch(engines.__name__ + '.PapermillExecutePreprocessor')
    def test_start_timeout(self, preproc_mock):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, start_timeout=123)
        preproc_mock.assert_called_once_with(
            timeout=None, startup_timeout=123, kernel_name=kernel_name, log=logger
        )

    @patch(engines.__name__ + '.PapermillExecutePreprocessor')
    def test_default_start_timeout(self, preproc_mock):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname)
        preproc_mock.assert_called_once_with(
            timeout=None, startup_timeout=60, kernel_name=kernel_name, log=logger
        )

    def test_cell_insertion(self):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, {'msg': 'Hello'})
        test_nb = load_notebook_node(self.nb_test_executed_fname)
        self.assertListEqual(
            test_nb.cells[1].get('source').split('\n'), ['# Parameters', 'msg = "Hello"', '']
        )
        self.assertEqual(test_nb.metadata.papermill.parameters, {'msg': 'Hello'})

    def test_no_tags(self):
        notebook_name = 'no_parameters.ipynb'
        nb_test_executed_fname = os.path.join(self.test_dir, 'output_{}'.format(notebook_name))
        execute_notebook(get_notebook_path(notebook_name), nb_test_executed_fname, {'msg': 'Hello'})
        test_nb = load_notebook_node(nb_test_executed_fname)
        self.assertListEqual(
            test_nb.cells[0].get('source').split('\n'), ['# Parameters', 'msg = "Hello"', '']
        )
        self.assertEqual(test_nb.metadata.papermill.parameters, {'msg': 'Hello'})

    def test_quoted_params(self):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, {'msg': '"Hello"'})
        test_nb = load_notebook_node(self.nb_test_executed_fname)
        self.assertListEqual(
            test_nb.cells[1].get('source').split('\n'), ['# Parameters', r'msg = "\"Hello\""', '']
        )
        self.assertEqual(test_nb.metadata.papermill.parameters, {'msg': '"Hello"'})

    def test_backslash_params(self):
        execute_notebook(
            self.notebook_path, self.nb_test_executed_fname, {'foo': r'do\ not\ crash'}
        )
        test_nb = load_notebook_node(self.nb_test_executed_fname)
        self.assertListEqual(
            test_nb.cells[1].get('source').split('\n'),
            ['# Parameters', r'foo = "do\\ not\\ crash"', ''],
        )
        self.assertEqual(test_nb.metadata.papermill.parameters, {'foo': r'do\ not\ crash'})

    def test_backslash_quote_params(self):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, {'foo': r'bar=\"baz\"'})
        test_nb = load_notebook_node(self.nb_test_executed_fname)
        self.assertListEqual(
            test_nb.cells[1].get('source').split('\n'),
            ['# Parameters', r'foo = "bar=\\\"baz\\\""', ''],
        )
        self.assertEqual(test_nb.metadata.papermill.parameters, {'foo': r'bar=\"baz\"'})

    def test_double_backslash_quote_params(self):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, {'foo': r'\\"bar\\"'})
        test_nb = load_notebook_node(self.nb_test_executed_fname)
        self.assertListEqual(
            test_nb.cells[1].get('source').split('\n'),
            ['# Parameters', r'foo = "\\\\\"bar\\\\\""', ''],
        )
        self.assertEqual(test_nb.metadata.papermill.parameters, {'foo': r'\\"bar\\"'})

    def test_prepare_only(self):
        for example in ['broken1.ipynb', 'keyboard_interrupt.ipynb']:
            path = get_notebook_path(example)
            result_path = os.path.join(self.test_dir, example)
            # Should not raise as we don't execute the notebook at all
            execute_notebook(path, result_path, {'foo': r'do\ not\ crash'}, prepare_only=True)
            nb = load_notebook_node(result_path)
            self.assertEqual(nb.cells[0].cell_type, "code")
            self.assertEqual(
                nb.cells[0].get('source').split('\n'),
                ['# Parameters', r'foo = "do\\ not\\ crash"', ''],
            )


class TestBrokenNotebook1(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test(self):
        path = get_notebook_path('broken1.ipynb')
        result_path = os.path.join(self.test_dir, 'broken1.ipynb')
        with self.assertRaises(PapermillExecutionError):
            execute_notebook(path, result_path)
        nb = load_notebook_node(result_path)
        self.assertEqual(nb.cells[0].cell_type, "code")
        self.assertEqual(nb.cells[0].outputs[0].output_type, "display_data")
        self.assertEqual(nb.cells[1].execution_count, 1)
        self.assertEqual(nb.cells[2].execution_count, 2)
        self.assertEqual(nb.cells[2].outputs[0].output_type, 'error')
        self.assertEqual(nb.cells[3].execution_count, None)


class TestBrokenNotebook2(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test(self):
        path = get_notebook_path('broken2.ipynb')
        result_path = os.path.join(self.test_dir, 'broken2.ipynb')
        with self.assertRaises(PapermillExecutionError):
            execute_notebook(path, result_path)
        nb = load_notebook_node(result_path)
        self.assertEqual(nb.cells[0].cell_type, "code")
        self.assertEqual(nb.cells[0].outputs[0].output_type, "display_data")
        self.assertEqual(nb.cells[1].execution_count, 1)
        self.assertEqual(nb.cells[2].execution_count, 2)
        self.assertEqual(nb.cells[2].outputs[0].output_type, 'display_data')
        self.assertEqual(nb.cells[2].outputs[1].output_type, 'error')
        self.assertEqual(nb.cells[3].execution_count, None)


class TestNBConvertCalls(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.notebook_name = 'simple_execute.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb_test_executed_fname = os.path.join(
            self.test_dir, 'output_{}'.format(self.notebook_name)
        )

        self.html_exporter = HTMLExporter()
        self.html_exporter.template_file = 'basic'

    def test_convert_output_to_html(self):
        execute_notebook(
            self.notebook_path,
            self.nb_test_executed_fname,
            {'msg': 'Hello'},
            engine_name='nbconvert',
        )
        test_nb = load_notebook_node(self.nb_test_executed_fname)

        # Ensure the notebook builds valid html without crashing
        (body, resources) = self.html_exporter.from_notebook_node(test_nb)
        self.assertTrue(body.startswith("\n<div"))


class TestReportMode(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.notebook_name = 'report_mode_test.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb_test_executed_fname = os.path.join(
            self.test_dir, 'output_{}'.format(self.notebook_name)
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_report_mode(self):
        nb = execute_notebook(
            self.notebook_path, self.nb_test_executed_fname, {'a': 0}, report_mode=True
        )
        for cell in nb.cells:
            if cell.cell_type == 'code':
                self.assertEqual(cell.metadata.get('jupyter', {}).get('source_hidden'), True)


class TestCWD(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_test_dir = tempfile.mkdtemp()

        self.check_notebook_name = 'read_check.ipynb'
        self.check_notebook_path = os.path.join(self.base_test_dir, 'read_check.ipynb')
        # Setup read paths so base_test_dir has check_notebook_name
        shutil.copyfile(get_notebook_path(self.check_notebook_name), self.check_notebook_path)
        with io.open(os.path.join(self.test_dir, 'check.txt'), 'w', encoding='utf-8') as f:
            # Needed for read_check to pass
            f.write(u'exists')

        self.simple_notebook_name = 'simple_execute.ipynb'
        self.simple_notebook_path = os.path.join(self.base_test_dir, 'simple_execute.ipynb')
        # Setup read paths so base_test_dir has simple_notebook_name
        shutil.copyfile(get_notebook_path(self.simple_notebook_name), self.simple_notebook_path)

        self.nb_test_executed_fname = 'test_output.ipynb'

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        shutil.rmtree(self.base_test_dir)

    def test_local_save_ignores_cwd_assignment(self):
        with chdir(self.base_test_dir):
            # Both paths are relative
            execute_notebook(
                self.simple_notebook_name, self.nb_test_executed_fname, cwd=self.test_dir
            )
        self.assertTrue(
            os.path.isfile(os.path.join(self.base_test_dir, self.nb_test_executed_fname))
        )

    def test_execution_respects_cwd_assignment(self):
        with chdir(self.base_test_dir):
            # Both paths are relative
            execute_notebook(
                self.check_notebook_name, self.nb_test_executed_fname, cwd=self.test_dir
            )
        self.assertTrue(
            os.path.isfile(os.path.join(self.base_test_dir, self.nb_test_executed_fname))
        )
