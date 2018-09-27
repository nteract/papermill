import sys
import mock
import datetime
import unittest

from . import get_notebook_path

from ..iorw import load_notebook_node
from ..engines import EngineNotebookWrapper

class TestEngineNotebookWrapper(unittest.TestCase):
    def setUp(self):
        self.notebook_name = 'simple_execute.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb = load_notebook_node(self.notebook_path)

    def test_basic_pbar(self):
        engine_nb = EngineNotebookWrapper(self.nb)

        self.assertEqual(engine_nb.pbar.total, len(self.nb.cells))
        self.assertEqual(engine_nb.pbar.gui, False)
        self.assertEqual(engine_nb.pbar.bar_format,
                         EngineNotebookWrapper.DEFAULT_BAR_FORMAT)

    def test_logging_pbar(self):
        engine_nb = EngineNotebookWrapper(self.nb, log_output=True)

        self.assertEqual(engine_nb.pbar.total, len(self.nb.cells))
        self.assertEqual(engine_nb.pbar.gui, False)
        self.assertEqual(engine_nb.pbar.bar_format,
                         EngineNotebookWrapper.DEFAULT_BAR_FORMAT + '\n')

    def test_notebook_pbar(self):
        # Need this or the tqdm notebook status printer fails
        with mock.patch('ipywidgets.IntProgress'):
            with mock.patch.dict(sys.modules, {'ipykernel': True}):
                engine_nb = EngineNotebookWrapper(self.nb)

        self.assertEqual(engine_nb.pbar.total, len(self.nb.cells))
        self.assertEqual(engine_nb.pbar.gui, True)
        self.assertEqual(engine_nb.pbar.bar_format, '{n}/|/{l_bar}{r_bar}')

    def test_no_pbar(self):
        engine_nb = EngineNotebookWrapper(self.nb, progress_bar=False)

        self.assertIsNone(engine_nb.pbar)

    def test_set_timer(self):
        now = datetime.datetime.utcnow()
        engine_nb = EngineNotebookWrapper(self.nb)

        with mock.patch.object(engine_nb, 'now', return_value=now):
            engine_nb.set_timer()

        self.assertEqual(engine_nb.start_time, now)
        self.assertIsNone(engine_nb.end_time)
