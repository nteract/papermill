import sys
import copy
import mock
import dateutil
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
        self.foo_nb = copy.deepcopy(self.nb)
        self.foo_nb.metadata['foo'] = 'bar'

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
        engine_nb = EngineNotebookWrapper(self.nb)
        now = engine_nb.now()

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
        engine_nb.save(nb=self.foo_nb)
        self.assertEqual(engine_nb.nb.metadata['foo'], 'bar')

    def test_notebook_start(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.save = mock.Mock()
        engine_nb.notebook_start()

        self.assertEqual(engine_nb.nb.metadata.papermill['start_time'],
                         engine_nb.start_time.isoformat())
        self.assertIsNone(engine_nb.nb.metadata.papermill['end_time'])
        self.assertIsNone(engine_nb.nb.metadata.papermill['duration'])
        self.assertIsNone(engine_nb.nb.metadata.papermill['exception'])

        for cell in engine_nb.nb.cells:
            self.assertIsNone(cell.metadata.papermill['start_time'])
            self.assertIsNone(cell.metadata.papermill['end_time'])
            self.assertIsNone(cell.metadata.papermill['duration'])
            self.assertIsNone(cell.metadata.papermill['exception'])
            self.assertEqual(cell.metadata.papermill['status'],
                             EngineNotebookWrapper.PENDING)
            self.assertIsNone(cell.execution_count)

        engine_nb.save.assert_called_once()

    def test_notebook_start_new_nb(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start(nb=self.foo_nb)
        self.assertEqual(engine_nb.nb.metadata['foo'], 'bar')

    def test_cell_start(self):
        engine_nb = EngineNotebookWrapper(self.nb)

        cell = engine_nb.nb.cells[0]
        fixed_now = engine_nb.now()

        engine_nb.now = mock.Mock(return_value=fixed_now)
        engine_nb.save = mock.Mock()
        engine_nb.cell_start(cell)

        self.assertEqual(cell.metadata.papermill['start_time'], fixed_now.isoformat())
        self.assertFalse(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'],
                         EngineNotebookWrapper.RUNNING)

        engine_nb.save.assert_called_once()

    def test_cell_start_new_nb(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.cell_start(self.foo_nb.cells[0], nb=self.foo_nb)
        self.assertEqual(engine_nb.nb.metadata['foo'], 'bar')

    def test_cell_exception(self):
        engine_nb = EngineNotebookWrapper(self.nb)

        cell = engine_nb.nb.cells[0]
        engine_nb.cell_exception(cell)

        self.assertEqual(engine_nb.nb.metadata.papermill['exception'], True)
        self.assertEqual(cell.metadata.papermill['exception'], True)
        self.assertEqual(cell.metadata.papermill['status'],
                         EngineNotebookWrapper.FAILED)

    def test_cell_exception_new_nb(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.cell_exception(self.foo_nb.cells[0], nb=self.foo_nb)
        self.assertEqual(engine_nb.nb.metadata['foo'], 'bar')

    def test_cell_complete_after_cell_start(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()
        cell = engine_nb.nb.cells[0]
        engine_nb.cell_start(cell)

        fixed_now = engine_nb.now()

        engine_nb.now = mock.Mock(return_value=fixed_now)
        engine_nb.save = mock.Mock()
        engine_nb.pbar.close()
        engine_nb.pbar = mock.Mock()
        engine_nb.cell_complete(cell)

        self.assertIsNotNone(cell.metadata['papermill']['start_time'])
        start_time = dateutil.parser.parse(cell.metadata['papermill']['start_time'])

        self.assertEqual(cell.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertEqual(cell.metadata.papermill['duration'],
                         (fixed_now - start_time).total_seconds())
        self.assertFalse(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'],
                         EngineNotebookWrapper.COMPLETED)

        engine_nb.save.assert_called_once()
        engine_nb.pbar.update.assert_called_once()

    def test_cell_complete_without_cell_start(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()
        cell = engine_nb.nb.cells[0]

        fixed_now = engine_nb.now()

        engine_nb.now = mock.Mock(return_value=fixed_now)
        engine_nb.save = mock.Mock()
        engine_nb.pbar.close()
        engine_nb.pbar = mock.Mock()
        engine_nb.cell_complete(cell)

        self.assertEqual(cell.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertIsNone(cell.metadata.papermill['duration'])
        self.assertFalse(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'],
                         EngineNotebookWrapper.COMPLETED)

        engine_nb.save.assert_called_once()
        engine_nb.pbar.update.assert_called_once()

    def test_cell_complete_after_cell_exception(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()
        cell = engine_nb.nb.cells[0]
        engine_nb.cell_start(cell)
        engine_nb.cell_exception(cell)

        fixed_now = engine_nb.now()

        engine_nb.now = mock.Mock(return_value=fixed_now)
        engine_nb.save = mock.Mock()
        engine_nb.pbar.close()
        engine_nb.pbar = mock.Mock()
        engine_nb.cell_complete(cell)

        self.assertIsNotNone(cell.metadata['papermill']['start_time'])
        start_time = dateutil.parser.parse(cell.metadata['papermill']['start_time'])

        self.assertEqual(cell.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertEqual(cell.metadata.papermill['duration'],
                         (fixed_now - start_time).total_seconds())
        self.assertTrue(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'],
                         EngineNotebookWrapper.FAILED)

        engine_nb.save.assert_called_once()
        engine_nb.pbar.update.assert_called_once()

    def test_cell_complete_new_nb(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()
        baz_nb = copy.deepcopy(engine_nb.nb)
        baz_nb.metadata['baz'] = 'buz'
        engine_nb.cell_complete(baz_nb.cells[0], nb=baz_nb)
        self.assertEqual(engine_nb.nb.metadata['baz'], 'buz')

    def test_notebook_complete(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()

        fixed_now = engine_nb.now()

        engine_nb.now = mock.Mock(return_value=fixed_now)
        engine_nb.save = mock.Mock()
        engine_nb.pbar.close()
        engine_nb.cleanup_pbar = mock.Mock()

        engine_nb.notebook_complete()

        self.assertIsNotNone(engine_nb.nb.metadata.papermill['start_time'])
        start_time = dateutil.parser.parse(engine_nb.nb.metadata.papermill['start_time'])

        self.assertEqual(engine_nb.nb.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertEqual(engine_nb.nb.metadata.papermill['duration'],
                         (fixed_now - start_time).total_seconds())
        self.assertFalse(engine_nb.nb.metadata.papermill['exception'])

        engine_nb.save.assert_called_once()
        engine_nb.cleanup_pbar.assert_called_once()

    def test_notebook_complete_new_nb(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()
        engine_nb.notebook_complete(nb=self.foo_nb)
        self.assertEqual(engine_nb.nb.metadata['foo'], 'bar')
