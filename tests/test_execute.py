import os
import shutil
import tempfile
import unittest


from papermill.api import read_notebook
from papermill.execute import execute_notebook
from tests import get_notebook_path


class TestNotebookHelpers(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test(self):
        nb_test1_fname = get_notebook_path('simple_execute.ipynb')
        nb_test1_executed_fname = os.path.join(self.test_dir, 'test1_executed.ipynb')
        execute_notebook(nb_test1_fname, nb_test1_executed_fname, {'msg': 'Hello'})
        test_nb = read_notebook(nb_test1_executed_fname)
        self.assertEqual(test_nb.node.cells[0].get('source'), u'# Parameters\nmsg = "Hello"\n')
        self.assertEqual(test_nb.parameters, {'msg': 'Hello'})


class TestBrokenNotebook(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test(self):
        path = get_notebook_path('broken.ipynb')
        result_path = os.path.join(self.test_dir, 'broken.ipynb')
        execute_notebook(path, result_path)
        nb = read_notebook(result_path)
        self.assertEqual(nb.node.cells[0].execution_count, 1)
        self.assertEqual(nb.node.cells[1].execution_count, 2)
        self.assertEqual(nb.node.cells[1].outputs[0].output_type, 'error')
        self.assertEqual(nb.node.cells[2].execution_count, None)
