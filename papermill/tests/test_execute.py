import os
import shutil
import tempfile
import unittest
from copy import deepcopy
from functools import partial
from pathlib import Path
from unittest.mock import ANY, patch

import nbformat
from colors import strip_color
from nbformat import validate

from .. import engines, translators
from ..exceptions import PapermillExecutionError
from ..execute import execute_notebook
from ..iorw import load_notebook_node
from ..log import logger
from ..utils import chdir
from . import get_notebook_path, kernel_name

execute_notebook = partial(execute_notebook, kernel_name=kernel_name)


class TestNotebookHelpers(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.notebook_name = 'simple_execute.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb_test_executed_fname = os.path.join(self.test_dir, f'output_{self.notebook_name}')

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch(f"{engines.__name__}.PapermillNotebookClient")
    def test_start_timeout(self, preproc_mock):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, start_timeout=123)
        args, kwargs = preproc_mock.call_args
        expected = [
            ('timeout', None),
            ('startup_timeout', 123),
            ('kernel_name', kernel_name),
            ('log', logger),
        ]
        actual = {(key, kwargs[key]) for key in kwargs}
        self.assertTrue(
            set(expected).issubset(actual),
            msg=f'Expected arguments {expected} are not a subset of actual {actual}',
        )

    @patch(f"{engines.__name__}.PapermillNotebookClient")
    def test_default_start_timeout(self, preproc_mock):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname)
        args, kwargs = preproc_mock.call_args
        expected = [
            ('timeout', None),
            ('startup_timeout', 60),
            ('kernel_name', kernel_name),
            ('log', logger),
        ]
        actual = {(key, kwargs[key]) for key in kwargs}
        self.assertTrue(
            set(expected).issubset(actual),
            msg=f'Expected arguments {expected} are not a subset of actual {actual}',
        )

    def test_cell_insertion(self):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, {'msg': 'Hello'})
        test_nb = load_notebook_node(self.nb_test_executed_fname)
        self.assertListEqual(test_nb.cells[1].get('source').split('\n'), ['# Parameters', 'msg = "Hello"', ''])
        self.assertEqual(test_nb.metadata.papermill.parameters, {'msg': 'Hello'})

    def test_no_tags(self):
        notebook_name = 'no_parameters.ipynb'
        nb_test_executed_fname = os.path.join(self.test_dir, f'output_{notebook_name}')
        execute_notebook(get_notebook_path(notebook_name), nb_test_executed_fname, {'msg': 'Hello'})
        test_nb = load_notebook_node(nb_test_executed_fname)
        self.assertListEqual(test_nb.cells[0].get('source').split('\n'), ['# Parameters', 'msg = "Hello"', ''])
        self.assertEqual(test_nb.metadata.papermill.parameters, {'msg': 'Hello'})

    def test_quoted_params(self):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, {'msg': '"Hello"'})
        test_nb = load_notebook_node(self.nb_test_executed_fname)
        self.assertListEqual(test_nb.cells[1].get('source').split('\n'), ['# Parameters', r'msg = "\"Hello\""', ''])
        self.assertEqual(test_nb.metadata.papermill.parameters, {'msg': '"Hello"'})

    def test_backslash_params(self):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, {'foo': r'do\ not\ crash'})
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

        # check that the notebook has two existing marker cells, so that this test is sure to be
        # validating the removal logic (the markers are simulatin an error in the first code cell
        # that has since been fixed)
        original_nb = load_notebook_node(path)
        self.assertEqual(original_nb.cells[0].metadata["tags"], ["papermill-error-cell-tag"])
        self.assertIn("In [1]", original_nb.cells[0].source)
        self.assertEqual(original_nb.cells[2].metadata["tags"], ["papermill-error-cell-tag"])

        result_path = os.path.join(self.test_dir, 'broken1.ipynb')
        with self.assertRaises(PapermillExecutionError):
            execute_notebook(path, result_path)
        nb = load_notebook_node(result_path)
        self.assertEqual(nb.cells[0].cell_type, "markdown")
        self.assertRegex(nb.cells[0].source, r'^<span .*<a href="#papermill-error-cell".*In \[2\].*</span>$')
        self.assertEqual(nb.cells[0].metadata["tags"], ["papermill-error-cell-tag"])

        self.assertEqual(nb.cells[1].cell_type, "markdown")
        self.assertEqual(nb.cells[2].execution_count, 1)
        self.assertEqual(nb.cells[3].cell_type, "markdown")
        self.assertEqual(nb.cells[4].cell_type, "markdown")

        self.assertEqual(nb.cells[5].cell_type, "markdown")
        self.assertRegex(nb.cells[5].source, '<span id="papermill-error-cell" .*</span>')
        self.assertEqual(nb.cells[5].metadata["tags"], ["papermill-error-cell-tag"])
        self.assertEqual(nb.cells[6].execution_count, 2)
        self.assertEqual(nb.cells[6].outputs[0].output_type, 'error')

        self.assertEqual(nb.cells[7].execution_count, None)

        # double check the removal (the new cells above should be the only two tagged ones)
        self.assertEqual(sum("papermill-error-cell-tag" in cell.metadata.get("tags", []) for cell in nb.cells), 2)


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
        self.assertEqual(nb.cells[0].cell_type, "markdown")
        self.assertRegex(nb.cells[0].source, r'^<span .*<a href="#papermill-error-cell">.*In \[2\].*</span>$')
        self.assertEqual(nb.cells[1].execution_count, 1)

        self.assertEqual(nb.cells[2].cell_type, "markdown")
        self.assertRegex(nb.cells[2].source, '<span id="papermill-error-cell" .*</span>')
        self.assertEqual(nb.cells[3].execution_count, 2)
        self.assertEqual(nb.cells[3].outputs[0].output_type, 'display_data')
        self.assertEqual(nb.cells[3].outputs[1].output_type, 'error')

        self.assertEqual(nb.cells[4].execution_count, None)


class TestReportMode(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.notebook_name = 'report_mode_test.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb_test_executed_fname = os.path.join(self.test_dir, f'output_{self.notebook_name}')

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_report_mode(self):
        nb = execute_notebook(self.notebook_path, self.nb_test_executed_fname, {'a': 0}, report_mode=True)
        for cell in nb.cells:
            if cell.cell_type == 'code':
                self.assertEqual(cell.metadata.get('jupyter', {}).get('source_hidden'), True)


class TestOutputPathNone(unittest.TestCase):
    def test_output_path_of_none(self):
        """Output path of None should return notebook node obj but not write an ipynb"""
        nb = execute_notebook(get_notebook_path('simple_execute.ipynb'), None, {'msg': 'Hello'})
        self.assertEqual(nb.metadata.papermill.parameters, {'msg': 'Hello'})


class TestCWD(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_test_dir = tempfile.mkdtemp()

        self.check_notebook_name = 'read_check.ipynb'
        self.check_notebook_path = os.path.join(self.base_test_dir, 'read_check.ipynb')
        # Setup read paths so base_test_dir has check_notebook_name
        shutil.copyfile(get_notebook_path(self.check_notebook_name), self.check_notebook_path)
        with open(os.path.join(self.test_dir, 'check.txt'), 'w', encoding='utf-8') as f:
            # Needed for read_check to pass
            f.write('exists')

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
            execute_notebook(self.simple_notebook_name, self.nb_test_executed_fname, cwd=self.test_dir)
        self.assertTrue(os.path.isfile(os.path.join(self.base_test_dir, self.nb_test_executed_fname)))

    def test_execution_respects_cwd_assignment(self):
        with chdir(self.base_test_dir):
            # Both paths are relative
            execute_notebook(self.check_notebook_name, self.nb_test_executed_fname, cwd=self.test_dir)
        self.assertTrue(os.path.isfile(os.path.join(self.base_test_dir, self.nb_test_executed_fname)))

    def test_pathlib_paths(self):
        # Copy of test_execution_respects_cwd_assignment but with `Path`s
        with chdir(self.base_test_dir):
            execute_notebook(
                Path(self.check_notebook_name),
                Path(self.nb_test_executed_fname),
                cwd=Path(self.test_dir),
            )
        self.assertTrue(Path(self.base_test_dir).joinpath(self.nb_test_executed_fname).exists())


class TestSysExit(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_sys_exit(self):
        notebook_name = 'sysexit.ipynb'
        result_path = os.path.join(self.test_dir, f'output_{notebook_name}')
        execute_notebook(get_notebook_path(notebook_name), result_path)
        nb = load_notebook_node(result_path)
        self.assertEqual(nb.cells[0].cell_type, "code")
        self.assertEqual(nb.cells[0].execution_count, 1)
        self.assertEqual(nb.cells[1].execution_count, 2)
        self.assertEqual(nb.cells[1].outputs[0].output_type, 'error')
        self.assertEqual(nb.cells[1].outputs[0].ename, 'SystemExit')
        self.assertEqual(nb.cells[1].outputs[0].evalue, '')
        self.assertEqual(nb.cells[2].execution_count, None)

    def test_sys_exit0(self):
        notebook_name = 'sysexit0.ipynb'
        result_path = os.path.join(self.test_dir, f'output_{notebook_name}')
        execute_notebook(get_notebook_path(notebook_name), result_path)
        nb = load_notebook_node(result_path)
        self.assertEqual(nb.cells[0].cell_type, "code")
        self.assertEqual(nb.cells[0].execution_count, 1)
        self.assertEqual(nb.cells[1].execution_count, 2)
        self.assertEqual(nb.cells[1].outputs[0].output_type, 'error')
        self.assertEqual(nb.cells[1].outputs[0].ename, 'SystemExit')
        self.assertEqual(nb.cells[1].outputs[0].evalue, '0')
        self.assertEqual(nb.cells[2].execution_count, None)

    def test_sys_exit1(self):
        notebook_name = 'sysexit1.ipynb'
        result_path = os.path.join(self.test_dir, f'output_{notebook_name}')
        with self.assertRaises(PapermillExecutionError):
            execute_notebook(get_notebook_path(notebook_name), result_path)
        nb = load_notebook_node(result_path)
        self.assertEqual(nb.cells[0].cell_type, "markdown")
        self.assertRegex(nb.cells[0].source, r'^<span .*<a href="#papermill-error-cell".*In \[2\].*</span>$')
        self.assertEqual(nb.cells[1].execution_count, 1)

        self.assertEqual(nb.cells[2].cell_type, "markdown")
        self.assertRegex(nb.cells[2].source, '<span id="papermill-error-cell" .*</span>')
        self.assertEqual(nb.cells[3].execution_count, 2)
        self.assertEqual(nb.cells[3].outputs[0].output_type, 'error')

        self.assertEqual(nb.cells[4].execution_count, None)

    def test_system_exit(self):
        notebook_name = 'systemexit.ipynb'
        result_path = os.path.join(self.test_dir, f'output_{notebook_name}')
        execute_notebook(get_notebook_path(notebook_name), result_path)
        nb = load_notebook_node(result_path)
        self.assertEqual(nb.cells[0].cell_type, "code")
        self.assertEqual(nb.cells[0].execution_count, 1)
        self.assertEqual(nb.cells[1].execution_count, 2)
        self.assertEqual(nb.cells[1].outputs[0].output_type, 'error')
        self.assertEqual(nb.cells[1].outputs[0].ename, 'SystemExit')
        self.assertEqual(nb.cells[1].outputs[0].evalue, '')
        self.assertEqual(nb.cells[2].execution_count, None)

    def test_line_magic_error(self):
        notebook_name = 'line_magic_error.ipynb'
        result_path = os.path.join(self.test_dir, f'output_{notebook_name}')
        with self.assertRaises(PapermillExecutionError):
            execute_notebook(get_notebook_path(notebook_name), result_path)
        nb = load_notebook_node(result_path)
        self.assertEqual(nb.cells[0].cell_type, "markdown")
        self.assertRegex(nb.cells[0].source, r'^<span .*<a href="#papermill-error-cell".*In \[1\].*</span>$')
        self.assertEqual(nb.cells[0].metadata["tags"], ["papermill-error-cell-tag"])
        self.assertEqual(nb.cells[2].cell_type, "code")
        self.assertEqual(nb.cells[2].execution_count, 1)
        self.assertEqual(nb.cells[3].execution_count, None)


class TestNotebookValidation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_from_version_4_4_upgrades(self):
        notebook_name = 'nb_version_4.4.ipynb'
        result_path = os.path.join(self.test_dir, f'output_{notebook_name}')
        execute_notebook(get_notebook_path(notebook_name), result_path, {'var': 'It works'})
        nb = load_notebook_node(result_path)
        validate(nb)


class TestMinimalNotebook(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_no_v3_language_backport(self):
        notebook_name = 'blank-vscode.ipynb'
        result_path = os.path.join(self.test_dir, f'output_{notebook_name}')
        execute_notebook(get_notebook_path(notebook_name), result_path, {'var': 'It works'})
        nb = load_notebook_node(result_path)
        validate(nb)


class TestExecuteWithCustomEngine(unittest.TestCase):
    class CustomEngine(engines.Engine):
        @classmethod
        def execute_managed_notebook(cls, nb_man, kernel_name, **kwargs):
            pass

        @classmethod
        def nb_kernel_name(cls, nb, name=None):
            return "my_custom_kernel"

        @classmethod
        def nb_language(cls, nb, language=None):
            return "my_custom_language"

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.notebook_path = get_notebook_path('simple_execute.ipynb')
        self.nb_test_executed_fname = os.path.join(self.test_dir, 'output_simple_execute.ipynb')

        self._orig_papermill_engines = deepcopy(engines.papermill_engines)
        self._orig_translators = deepcopy(translators.papermill_translators)
        engines.papermill_engines.register("custom_engine", self.CustomEngine)
        translators.papermill_translators.register("my_custom_language", translators.PythonTranslator())

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        engines.papermill_engines = self._orig_papermill_engines
        translators.papermill_translators = self._orig_translators

    @patch.object(CustomEngine, "execute_managed_notebook", wraps=CustomEngine.execute_managed_notebook)
    @patch("papermill.parameterize.translate_parameters", wraps=translators.translate_parameters)
    def test_custom_kernel_name_and_language(self, translate_parameters, execute_managed_notebook):
        """Tests execute against engine with custom implementations to fetch
        kernel name and language from the notebook object
        """
        execute_notebook(
            self.notebook_path,
            self.nb_test_executed_fname,
            engine_name="custom_engine",
            parameters={"msg": "fake msg"},
        )
        self.assertEqual(execute_managed_notebook.call_args[0], (ANY, "my_custom_kernel"))
        self.assertEqual(translate_parameters.call_args[0], (ANY, 'my_custom_language', {"msg": "fake msg"}, ANY))


class TestNotebookNodeInput(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.result_path = os.path.join(self.test_dir.name, 'output.ipynb')

    def tearDown(self):
        self.test_dir.cleanup()

    def test_notebook_node_input(self):
        input_nb = nbformat.read(get_notebook_path('simple_execute.ipynb'), as_version=4)
        execute_notebook(input_nb, self.result_path, {'msg': 'Hello'})
        test_nb = nbformat.read(self.result_path, as_version=4)
        self.assertEqual(test_nb.metadata.papermill.parameters, {'msg': 'Hello'})


class TestOutputFormatting(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_output_formatting(self):
        notebook_name = 'sysexit1.ipynb'
        result_path = os.path.join(self.test_dir, f'output_{notebook_name}')
        try:
            execute_notebook(get_notebook_path(notebook_name), result_path)
            # exception should be thrown by now
            self.assertFalse(True)
        except PapermillExecutionError as ex:
            self.assertEqual(ex.traceback[1], "\x1b[0;31mSystemExit\x1b[0m\x1b[0;31m:\x1b[0m 1\n")
            self.assertEqual(strip_color(ex.traceback[1]), "SystemExit: 1\n")

        nb = load_notebook_node(result_path)
        self.assertEqual(nb.cells[0].cell_type, "markdown")
        self.assertRegex(nb.cells[0].source, r'^<span .*<a href="#papermill-error-cell".*In \[2\].*</span>$')
        self.assertEqual(nb.cells[1].execution_count, 1)

        self.assertEqual(nb.cells[2].cell_type, "markdown")
        self.assertRegex(nb.cells[2].source, '<span id="papermill-error-cell" .*</span>')
        self.assertEqual(nb.cells[3].execution_count, 2)
        self.assertEqual(nb.cells[3].outputs[0].output_type, 'error')

        self.assertEqual(nb.cells[4].execution_count, None)
