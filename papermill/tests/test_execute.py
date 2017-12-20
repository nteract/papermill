import io
import os
import pytest
import shutil
import sys
import tempfile
import unittest

import nbformat

from ..api import read_notebook
from ..execute import execute_notebook, log_outputs
from ..exceptions import PapermillExecutionError
from . import get_notebook_path, RedirectOutput

python_2 = sys.version_info[0] == 2

class TestNotebookHelpers(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.notebook_name = 'simple_execute_2.ipynb' if python_2 else 'simple_execute.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb_test_executed_fname = os.path.join(self.test_dir, 'output_{}'.format(self.notebook_name))

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_cell_insertion(self):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, {'msg': 'Hello'})
        test_nb = read_notebook(self.nb_test_executed_fname)
        self.assertEqual(test_nb.node.cells[1].get('source'), u'# Parameters\nmsg = "Hello"\n')
        self.assertEqual(test_nb.parameters, {'msg': 'Hello'})

    def test_no_tags(self):
        notebook_name = 'no_parameters.ipynb'
        nb_test_executed_fname = os.path.join(self.test_dir, 'output_{}'.format(notebook_name))
        execute_notebook(get_notebook_path(notebook_name), nb_test_executed_fname, {'msg': 'Hello'})
        test_nb = read_notebook(nb_test_executed_fname)
        self.assertEqual(test_nb.node.cells[0].get('source'), u'# Parameters\nmsg = "Hello"\n')
        self.assertEqual(test_nb.parameters, {'msg': 'Hello'})

    def test_quoted_params(self):
        execute_notebook(self.notebook_path, self.nb_test_executed_fname, {'msg': '"Hello"'})
        test_nb = read_notebook(self.nb_test_executed_fname)
        self.assertEqual(test_nb.node.cells[1].get('source'), u'# Parameters\nmsg = "\\"Hello\\""\n')
        self.assertEqual(test_nb.parameters, {'msg': '"Hello"'})


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
        nb = read_notebook(result_path)
        self.assertEqual(nb.node.cells[0].cell_type, "markdown")
        self.assertEqual(nb.node.cells[1].execution_count, 1)
        self.assertEqual(nb.node.cells[2].execution_count, 2)
        self.assertEqual(nb.node.cells[2].outputs[0].output_type, 'error')
        self.assertEqual(nb.node.cells[3].execution_count, None)


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
        nb = read_notebook(result_path)
        self.assertEqual(nb.node.cells[0].cell_type, "markdown")
        self.assertEqual(nb.node.cells[1].execution_count, 1)
        self.assertEqual(nb.node.cells[2].execution_count, 2)
        self.assertEqual(nb.node.cells[2].outputs[0].output_type, 'display_data')
        self.assertEqual(nb.node.cells[2].outputs[1].output_type, 'error')
        self.assertEqual(nb.node.cells[3].execution_count, None)


class TestLogging(unittest.TestCase):

    def setUp(self):
        self.saved_stdout = sys.stdout
        self.out = io.StringIO()
        sys.stdout = self.out

    def tearDown(self):
        sys.stdout = self.saved_stdout

    def test_logging(self):

        nb = nbformat.read(get_notebook_path('test_logging.ipynb'), as_version=4)

        # stderr output
        with RedirectOutput() as redirect:
            log_outputs(nb.cells[0])
            stdout = redirect.get_stdout()
            self.assertEqual(stdout, u'Out [1] --------------------------------\n\n')
            stderr = redirect.get_stderr()
            self.assertEqual(stderr, u'Out [1] --------------------------------\nINFO:test:test text\n\n')

        # stream output
        with RedirectOutput() as redirect:
            log_outputs(nb.cells[1])
            stdout = redirect.get_stdout()
            self.assertEqual(stdout, u'Out [2] --------------------------------\nhello world\n\n')
            stderr = redirect.get_stderr()
            self.assertEqual(stderr, u'Out [2] --------------------------------\n\n')

        # text/plain output
        with RedirectOutput() as redirect:
            log_outputs(nb.cells[2])
            stdout = redirect.get_stdout()
            self.assertEqual(stdout,
                             (
                                "Out [3] --------------------------------\n"
                                "<matplotlib.axes._subplots.AxesSubplot at 0x7f8391f10290>\n"
                                "<matplotlib.figure.Figure at 0x7f830af7b350>\n"
                                )
                             )
            stderr = redirect.get_stderr()
            self.assertEqual(stderr, u'Out [3] --------------------------------\n\n')
