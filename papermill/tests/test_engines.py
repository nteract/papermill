import sys
import abc
import copy
import dateutil
import unittest

from mock import Mock, PropertyMock, patch
from nbformat.notebooknode import NotebookNode

from . import get_notebook_path

from .. import engines
from ..iorw import load_notebook_node
from ..engines import EngineNotebookWrapper, EngineBase, NBConvertEngine


# ABC inheritable compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


def AnyMock(cls):
    """
    Mocks a matcher for any instance of class cls.
    e.g. my_mock.called_once_with(Any(int), "bar")
    """

    class AnyMock(ABC):
        def __eq__(self, other):
            return isinstance(other, cls)

    AnyMock.register(cls)
    return AnyMock()


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
        self.assertEqual(engine_nb.pbar.bar_format, EngineNotebookWrapper.DEFAULT_BAR_FORMAT)

    def test_logging_pbar(self):
        engine_nb = EngineNotebookWrapper(self.nb, log_output=True)

        self.assertEqual(engine_nb.pbar.total, len(self.nb.cells))
        self.assertEqual(engine_nb.pbar.gui, False)
        self.assertEqual(engine_nb.pbar.bar_format, EngineNotebookWrapper.DEFAULT_BAR_FORMAT + '\n')

    def test_notebook_pbar(self):
        # Need this or the tqdm notebook status printer fails
        with patch('ipywidgets.HBox'):
            with patch('ipywidgets.IntProgress'):
                with patch.dict(sys.modules, {'ipykernel': True}):
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

        with patch.object(engine_nb, 'now', return_value=now):
            engine_nb.set_timer()

        self.assertEqual(engine_nb.start_time, now)
        self.assertIsNone(engine_nb.end_time)

    def test_save(self):
        engine_nb = EngineNotebookWrapper(self.nb, output_path='test.ipynb')
        with patch.object(engines, 'write_ipynb') as write_mock:
            engine_nb.save()
            write_mock.assert_called_with(self.nb, 'test.ipynb')

    def test_save_no_output(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        with patch.object(engines, 'write_ipynb') as write_mock:
            engine_nb.save()
            write_mock.assert_not_called()

    def test_save_new_nb(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.save(nb=self.foo_nb)
        self.assertEqual(engine_nb.nb.metadata['foo'], 'bar')

    def test_notebook_start(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.save = Mock()
        engine_nb.notebook_start()

        self.assertEqual(
            engine_nb.nb.metadata.papermill['start_time'], engine_nb.start_time.isoformat()
        )
        self.assertIsNone(engine_nb.nb.metadata.papermill['end_time'])
        self.assertIsNone(engine_nb.nb.metadata.papermill['duration'])
        self.assertIsNone(engine_nb.nb.metadata.papermill['exception'])

        for cell in engine_nb.nb.cells:
            self.assertIsNone(cell.metadata.papermill['start_time'])
            self.assertIsNone(cell.metadata.papermill['end_time'])
            self.assertIsNone(cell.metadata.papermill['duration'])
            self.assertIsNone(cell.metadata.papermill['exception'])
            self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.PENDING)
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

        engine_nb.now = Mock(return_value=fixed_now)
        engine_nb.save = Mock()
        engine_nb.cell_start(cell)

        self.assertEqual(cell.metadata.papermill['start_time'], fixed_now.isoformat())
        self.assertFalse(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.RUNNING)

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
        self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.FAILED)

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

        engine_nb.now = Mock(return_value=fixed_now)
        engine_nb.save = Mock()
        engine_nb.pbar.close()
        engine_nb.pbar = Mock()
        engine_nb.cell_complete(cell)

        self.assertIsNotNone(cell.metadata.papermill['start_time'])
        start_time = dateutil.parser.parse(cell.metadata.papermill['start_time'])

        self.assertEqual(cell.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertEqual(
            cell.metadata.papermill['duration'], (fixed_now - start_time).total_seconds()
        )
        self.assertFalse(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.COMPLETED)

        engine_nb.save.assert_called_once()
        engine_nb.pbar.update.assert_called_once()

    def test_cell_complete_without_cell_start(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()
        cell = engine_nb.nb.cells[0]

        fixed_now = engine_nb.now()

        engine_nb.now = Mock(return_value=fixed_now)
        engine_nb.save = Mock()
        engine_nb.pbar.close()
        engine_nb.pbar = Mock()
        engine_nb.cell_complete(cell)

        self.assertEqual(cell.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertIsNone(cell.metadata.papermill['duration'])
        self.assertFalse(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.COMPLETED)

        engine_nb.save.assert_called_once()
        engine_nb.pbar.update.assert_called_once()

    def test_cell_complete_after_cell_exception(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()
        cell = engine_nb.nb.cells[0]
        engine_nb.cell_start(cell)
        engine_nb.cell_exception(cell)

        fixed_now = engine_nb.now()

        engine_nb.now = Mock(return_value=fixed_now)
        engine_nb.save = Mock()
        engine_nb.pbar.close()
        engine_nb.pbar = Mock()
        engine_nb.cell_complete(cell)

        self.assertIsNotNone(cell.metadata.papermill['start_time'])
        start_time = dateutil.parser.parse(cell.metadata.papermill['start_time'])

        self.assertEqual(cell.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertEqual(
            cell.metadata.papermill['duration'], (fixed_now - start_time).total_seconds()
        )
        self.assertTrue(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.FAILED)

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

        engine_nb.now = Mock(return_value=fixed_now)
        engine_nb.save = Mock()
        engine_nb.pbar.close()
        engine_nb.cleanup_pbar = Mock()

        engine_nb.notebook_complete()

        self.assertIsNotNone(engine_nb.nb.metadata.papermill['start_time'])
        start_time = dateutil.parser.parse(engine_nb.nb.metadata.papermill['start_time'])

        self.assertEqual(engine_nb.nb.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertEqual(
            engine_nb.nb.metadata.papermill['duration'], (fixed_now - start_time).total_seconds()
        )
        self.assertFalse(engine_nb.nb.metadata.papermill['exception'])

        engine_nb.save.assert_called_once()
        engine_nb.cleanup_pbar.assert_called_once()

    def test_notebook_complete_new_nb(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()
        baz_nb = copy.deepcopy(engine_nb.nb)
        baz_nb.metadata['baz'] = 'buz'
        engine_nb.notebook_complete(nb=baz_nb)
        self.assertEqual(engine_nb.nb.metadata['baz'], 'buz')

    def test_notebook_complete_cell_status_completed(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()
        engine_nb.notebook_complete()
        for cell in engine_nb.nb.cells:
            self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.COMPLETED)

    def test_notebook_complete_cell_status_with_failed(self):
        engine_nb = EngineNotebookWrapper(self.nb)
        engine_nb.notebook_start()
        engine_nb.cell_exception(engine_nb.nb.cells[1])
        engine_nb.notebook_complete()
        self.assertEqual(
            engine_nb.nb.cells[0].metadata.papermill['status'], EngineNotebookWrapper.COMPLETED
        )
        self.assertEqual(
            engine_nb.nb.cells[1].metadata.papermill['status'], EngineNotebookWrapper.FAILED
        )
        for cell in engine_nb.nb.cells[2:]:
            self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.PENDING)


class TestEngineBase(unittest.TestCase):
    def setUp(self):
        self.notebook_name = 'simple_execute.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb = load_notebook_node(self.notebook_path)

    def test_wrap_and_execute_notebook(self):
        '''
        Mocks each wrapped call and proves the correct inputs get applies to
        the correct underlying calls for wrap_and_execute_notebook.
        '''
        with patch.object(EngineBase, 'execute_notebook') as exec_mock:
            with patch.object(engines, 'EngineNotebookWrapper') as wrap_mock:
                EngineBase.wrap_and_execute_notebook(
                    self.nb,
                    'python',
                    output_path='foo.ipynb',
                    progress_bar=False,
                    log_output=True,
                    bar='baz',
                )

                wrap_mock.assert_called_once_with(
                    self.nb, output_path='foo.ipynb', progress_bar=False, log_output=True
                )
                wrap_mock.return_value.notebook_start.assert_called_once()
                exec_mock.assert_called_once_with(
                    wrap_mock.return_value, 'python', log_output=True, bar='baz'
                )
                wrap_mock.return_value.notebook_complete.assert_called_once()
                wrap_mock.return_value.cleanup_pbar.assert_called_once()

    def test_cell_callback_execute(self):
        class CellCallbackEngine(EngineBase):
            @classmethod
            def execute_notebook(cls, engine_nb, kernel_name, **kwargs):
                for cell in engine_nb.nb.cells:
                    engine_nb.cell_start(cell)
                    engine_nb.cell_complete(cell)

        with patch.object(EngineNotebookWrapper, 'save') as save_mock:
            nb = CellCallbackEngine.wrap_and_execute_notebook(
                self.nb, 'python', output_path='foo.ipynb'
            )

            self.assertEqual(nb, AnyMock(NotebookNode))
            self.assertNotEqual(self.nb, nb)

            self.assertEqual(save_mock.call_count, 8)

            self.assertIsNotNone(nb.metadata.papermill['start_time'])
            self.assertIsNotNone(nb.metadata.papermill['end_time'])
            self.assertEqual(nb.metadata.papermill['duration'], AnyMock(float))
            self.assertFalse(nb.metadata.papermill['exception'])

            for cell in nb.cells:
                self.assertIsNotNone(cell.metadata.papermill['start_time'])
                self.assertIsNotNone(cell.metadata.papermill['end_time'])
                self.assertEqual(cell.metadata.papermill['duration'], AnyMock(float))
                self.assertFalse(cell.metadata.papermill['exception'])
                self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.COMPLETED)

    def test_no_cell_callback_execute(self):
        class NoCellCallbackEngine(EngineBase):
            @classmethod
            def execute_notebook(cls, engine_nb, kernel_name, **kwargs):
                pass

        with patch.object(EngineNotebookWrapper, 'save') as save_mock:
            nb = NoCellCallbackEngine.wrap_and_execute_notebook(
                self.nb, 'python', output_path='foo.ipynb'
            )

            self.assertEqual(nb, AnyMock(NotebookNode))
            self.assertNotEqual(self.nb, nb)

            self.assertEqual(save_mock.call_count, 2)

            self.assertIsNotNone(nb.metadata.papermill['start_time'])
            self.assertIsNotNone(nb.metadata.papermill['end_time'])
            self.assertEqual(nb.metadata.papermill['duration'], AnyMock(float))
            self.assertFalse(nb.metadata.papermill['exception'])

            for cell in nb.cells:
                self.assertIsNone(cell.metadata.papermill['start_time'])
                self.assertIsNone(cell.metadata.papermill['end_time'])
                self.assertIsNone(cell.metadata.papermill['duration'])
                self.assertIsNone(cell.metadata.papermill['exception'])
                self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.COMPLETED)


class TestNBConvertEngine(unittest.TestCase):
    def setUp(self):
        self.notebook_name = 'simple_execute.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb = load_notebook_node(self.notebook_path)

    def test_nb_convert_engine(self):
        with patch.object(engines, 'PapermillExecutePreprocessor') as pep_mock:
            # Mock log_output calls
            log_out_mock = PropertyMock()
            type(pep_mock.return_value).log_output = log_out_mock

            with patch.object(EngineNotebookWrapper, 'save') as save_mock:
                nb = NBConvertEngine.wrap_and_execute_notebook(
                    self.nb,
                    'python',
                    output_path='foo.ipynb',
                    progress_bar=False,
                    log_output=True,
                    bar='baz',
                    start_timeout=30,
                    execution_timeout=1000,
                )

                self.assertEqual(nb, AnyMock(NotebookNode))
                self.assertNotEqual(self.nb, nb)

                pep_mock.assert_called_once()
                pep_mock.assert_called_once_with(
                    timeout=1000, startup_timeout=30, kernel_name='python'
                )
                log_out_mock.assert_called_once_with(True)
                pep_mock.return_value.preprocess.assert_called_once_with(
                    AnyMock(EngineNotebookWrapper), {'bar': 'baz'}
                )
                # Once for start and once for complete (cell not called by mock)
                self.assertEqual(save_mock.call_count, 2)

    def test_nb_convert_engine_execute(self):
        with patch.object(EngineNotebookWrapper, 'save') as save_mock:
            nb = NBConvertEngine.wrap_and_execute_notebook(
                self.nb, 'python', output_path='foo.ipynb', progress_bar=False, log_output=False
            )
            self.assertEqual(save_mock.call_count, 8)
            self.assertEqual(nb, AnyMock(NotebookNode))

            self.assertIsNotNone(nb.metadata.papermill['start_time'])
            self.assertIsNotNone(nb.metadata.papermill['end_time'])
            self.assertEqual(nb.metadata.papermill['duration'], AnyMock(float))
            self.assertFalse(nb.metadata.papermill['exception'])

            for cell in nb.cells:
                self.assertIsNotNone(cell.metadata.papermill['start_time'])
                self.assertIsNotNone(cell.metadata.papermill['end_time'])
                self.assertEqual(cell.metadata.papermill['duration'], AnyMock(float))
                self.assertFalse(cell.metadata.papermill['exception'])
                self.assertEqual(cell.metadata.papermill['status'], EngineNotebookWrapper.COMPLETED)
