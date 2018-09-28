import sys
import mock
import datetime
import unittest

from . import get_notebook_path

from .. import engines
from ..iorw import load_notebook_node
from ..engines import EngineNotebookWrapper


class TestEngineNotebookWrapper(unittest.TestCase):
    def setUp(self):
        self.notebook_name = 'simple_execute.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb = load_notebook_node(self.notebook_path)

    def test_nb_isolation(self):
        """
        Tests that the engine notebook is isolated from source notebook
        """
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.nb.metadata['foo'] = 'bar'
        self.assertNotEqual(engine_nb.nb, self.nb)

    def test_basic_pbar(self):
        engine_nb = EngineNotebookWrapper(self.nb)

        self.assertEqual(engine_nb.pbar.total, len(self.nb.cells))
        self.assertEqual(engine_nb.pbar.gui, False)
        self.assertEqual(engine_nb.pbar.bar_format, EngineNotebookWrapper.DEFAULT_BAR_FORMAT)

    def test_logging_pbar(self):
        engine_nb = EngineNotebookWrapper(self.nb, log_output=True)

        self.assertEqual(engine_nb.pbar.total, len(self.nb.cells))
        self.assertEqual(engine_nb.pbar.gui, False)
        self.assertEqual(engine_nb.pbar.bar_format, EngineNotebookWrapper.DEFAULT_BAR_FORMAT + '\n')

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

    def test_save(self):
        engine_nb = EngineNotebookWrapper(self.nb, output_path='test.ipynb')
        with mock.patch.object(engines, 'write_ipynb') as write_mock:
            engine_nb.save()
            write_mock.assert_called_with(self.nb, 'test.ipynb')

    def test_save_no_output(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        with mock.patch.object(engines, 'write_ipynb') as write_mock:
            engine_nb.save()
            write_mock.assert_not_called()

    def test_save_new_nb(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        new_nb = {'foo': 'bar'}
        engine_nb.save(nb=new_nb)
        self.assertEqual(engine_nb.nb, new_nb)

    def test_notebook_start(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()

        self.assertEqual(engine_nb.nb.metadata.papermill['start_time'], engine_nb.start_time.isoformat())
        self.assertIsNone(engine_nb.nb.metadata.papermill['end_time'])
        self.assertIsNone(engine_nb.nb.metadata.papermill['duration'])
        self.assertIsNone(engine_nb.nb.metadata.papermill['exception'])

        for cell in engine_nb.nb.cells:
            self.assertIsNone(cell.metadata.papermill['start_time'])
            self.assertIsNone(cell.metadata.papermill['end_time'])
            self.assertIsNone(cell.metadata.papermill['duration'])
            self.assertIsNone(cell.metadata.papermill['exception'])
            self.assertIsEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.PENDING)
            self.assertIsNone(cell.execution_count)
