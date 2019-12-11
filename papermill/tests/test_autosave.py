import nbformat
import os
import tempfile
import time
import unittest

from mock import patch

from . import get_notebook_path

from .. import engines
from ..engines import NotebookExecutionManager
from ..execute import execute_notebook


class TestMidCellAutosave(unittest.TestCase):
    def setUp(self):
        self.notebook_name = 'test_autosave.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb = nbformat.read(self.notebook_path, as_version=4)

    def test_autosave_not_too_fast(self):
        nb_man = NotebookExecutionManager(
            self.nb, output_path='test.ipynb', autosave_cell_every=0.5
        )
        with patch.object(engines, 'write_ipynb') as write_mock:
            write_mock.reset_mock()
            assert write_mock.call_count == 0  # check that the mock is sane
            nb_man.autosave_cell()  # First call to autosave shouldn't trigger save
            assert write_mock.call_count == 0
            nb_man.autosave_cell()  # Call again right away.  Still shouldn't save.
            assert write_mock.call_count == 0
            time.sleep(0.55)  # Sleep for long enough that autosave should work
            nb_man.autosave_cell()
            assert write_mock.call_count == 1

    def test_autosave_disable(self):
        nb_man = NotebookExecutionManager(self.nb, output_path='test.ipynb', autosave_cell_every=0)
        with patch.object(engines, 'write_ipynb') as write_mock:
            write_mock.reset_mock()
            assert write_mock.call_count == 0  # check that the mock is sane
            nb_man.autosave_cell()  # First call to autosave shouldn't trigger save
            assert write_mock.call_count == 0
            nb_man.autosave_cell()  # Call again right away.  Still shouldn't save.
            assert write_mock.call_count == 0
            time.sleep(0.55)  # Sleep for long enough that autosave should work, if enabled
            nb_man.autosave_cell()
            assert write_mock.call_count == 0  # but it's disabled.

    def test_end2end_autosave_slow_notebook(self):
        test_dir = tempfile.mkdtemp()
        nb_test_executed_fname = os.path.join(test_dir, 'output_{}'.format(self.notebook_name))
        with patch.object(engines, 'write_ipynb') as write_mock:
            # This notebook has a cell which takes 2.5 seconds to run
            execute_notebook(self.notebook_path, nb_test_executed_fname, autosave_cell_ever=1)
            assert (
                write_mock.call_count == 4
            )  # Saves twice normally, and 2x autosave during slow cell.
