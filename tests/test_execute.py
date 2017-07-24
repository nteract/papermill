import os
import shutil
import tempfile
import unittest


from papermill.api import Notebook
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
        test_nb = Notebook.read(nb_test1_executed_fname)
        self.assertEqual(test_nb.nb_node.cells[0].get('source'), u'# Parameters\nmsg = "Hello"\n')
        self.assertEqual(test_nb.parameters, {'msg': 'Hello'})
