import abc
import copy
import dateutil
import unittest

from mock import Mock, PropertyMock, patch, call
from nbformat.notebooknode import NotebookNode

from . import get_notebook_path

from .. import engines, exceptions
from ..log import logger
from ..iorw import load_notebook_node
from ..engines import NotebookExecutionManager, Engine, NBConvertEngine


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


class TestNotebookExecutionManager(unittest.TestCase):
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
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.nb.metadata['foo'] = 'bar'
        self.assertNotEqual(nb_man.nb, self.nb)

    def test_basic_pbar(self):
        nb_man = NotebookExecutionManager(self.nb)

        self.assertEqual(nb_man.pbar.total, len(self.nb.cells))
        self.assertEqual(nb_man.pbar.gui, False)
        self.assertEqual(nb_man.pbar.bar_format, NotebookExecutionManager.DEFAULT_BAR_FORMAT)

    def test_logging_pbar(self):
        nb_man = NotebookExecutionManager(self.nb, log_output=True)

        self.assertEqual(nb_man.pbar.total, len(self.nb.cells))
        self.assertEqual(nb_man.pbar.gui, False)
        self.assertEqual(nb_man.pbar.bar_format, NotebookExecutionManager.DEFAULT_BAR_FORMAT + '\n')

    def test_notebook_pbar(self):
        # Need this or the tqdm notebook status printer fails
        with patch.object(engines, 'using_ipykernel', return_value=True):
            with patch('ipywidgets.HBox'):
                with patch('ipywidgets.IntProgress'):
                    nb_man = NotebookExecutionManager(self.nb)

            self.assertEqual(nb_man.pbar.total, len(self.nb.cells))
            self.assertEqual(nb_man.pbar.gui, True)
            self.assertEqual(nb_man.pbar.bar_format, '{n}/|/{l_bar}{r_bar}')

    def test_no_pbar(self):
        nb_man = NotebookExecutionManager(self.nb, progress_bar=False)

        self.assertIsNone(nb_man.pbar)

    def test_set_timer(self):
        nb_man = NotebookExecutionManager(self.nb)
        now = nb_man.now()

        with patch.object(nb_man, 'now', return_value=now):
            nb_man.set_timer()

        self.assertEqual(nb_man.start_time, now)
        self.assertIsNone(nb_man.end_time)

    def test_save(self):
        nb_man = NotebookExecutionManager(self.nb, output_path='test.ipynb')
        with patch.object(engines, 'write_ipynb') as write_mock:
            nb_man.save()
            write_mock.assert_called_with(self.nb, 'test.ipynb')

    def test_save_no_output(self):
        nb_man = NotebookExecutionManager(self.nb)
        with patch.object(engines, 'write_ipynb') as write_mock:
            nb_man.save()
            write_mock.assert_not_called()

    def test_save_new_nb(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.save(nb=self.foo_nb)
        self.assertEqual(nb_man.nb.metadata['foo'], 'bar')

    def test_notebook_start(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.save = Mock()
        nb_man.notebook_start()

        self.assertEqual(nb_man.nb.metadata.papermill['start_time'], nb_man.start_time.isoformat())
        self.assertIsNone(nb_man.nb.metadata.papermill['end_time'])
        self.assertIsNone(nb_man.nb.metadata.papermill['duration'])
        self.assertIsNone(nb_man.nb.metadata.papermill['exception'])

        for cell in nb_man.nb.cells:
            self.assertIsNone(cell.metadata.papermill['start_time'])
            self.assertIsNone(cell.metadata.papermill['end_time'])
            self.assertIsNone(cell.metadata.papermill['duration'])
            self.assertIsNone(cell.metadata.papermill['exception'])
            self.assertEqual(cell.metadata.papermill['status'], NotebookExecutionManager.PENDING)
            self.assertIsNone(cell.execution_count)

        nb_man.save.assert_called_once()

    def test_notebook_start_new_nb(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.notebook_start(nb=self.foo_nb)
        self.assertEqual(nb_man.nb.metadata['foo'], 'bar')

    def test_cell_start(self):
        nb_man = NotebookExecutionManager(self.nb)

        cell = nb_man.nb.cells[0]
        fixed_now = nb_man.now()

        nb_man.now = Mock(return_value=fixed_now)
        nb_man.save = Mock()
        nb_man.cell_start(cell)

        self.assertEqual(cell.metadata.papermill['start_time'], fixed_now.isoformat())
        self.assertFalse(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'], NotebookExecutionManager.RUNNING)

        nb_man.save.assert_called_once()

    def test_cell_start_new_nb(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.cell_start(self.foo_nb.cells[0], nb=self.foo_nb)
        self.assertEqual(nb_man.nb.metadata['foo'], 'bar')

    def test_cell_exception(self):
        nb_man = NotebookExecutionManager(self.nb)

        cell = nb_man.nb.cells[0]
        nb_man.cell_exception(cell)

        self.assertEqual(nb_man.nb.metadata.papermill['exception'], True)
        self.assertEqual(cell.metadata.papermill['exception'], True)
        self.assertEqual(cell.metadata.papermill['status'], NotebookExecutionManager.FAILED)

    def test_cell_exception_new_nb(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.cell_exception(self.foo_nb.cells[0], nb=self.foo_nb)
        self.assertEqual(nb_man.nb.metadata['foo'], 'bar')

    def test_cell_complete_after_cell_start(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.notebook_start()
        cell = nb_man.nb.cells[0]
        nb_man.cell_start(cell)

        fixed_now = nb_man.now()

        nb_man.now = Mock(return_value=fixed_now)
        nb_man.save = Mock()
        nb_man.pbar.close()
        nb_man.pbar = Mock()
        nb_man.cell_complete(cell)

        self.assertIsNotNone(cell.metadata.papermill['start_time'])
        start_time = dateutil.parser.parse(cell.metadata.papermill['start_time'])

        self.assertEqual(cell.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertEqual(
            cell.metadata.papermill['duration'], (fixed_now - start_time).total_seconds()
        )
        self.assertFalse(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'], NotebookExecutionManager.COMPLETED)

        nb_man.save.assert_called_once()
        nb_man.pbar.update.assert_called_once()

    def test_cell_complete_without_cell_start(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.notebook_start()
        cell = nb_man.nb.cells[0]

        fixed_now = nb_man.now()

        nb_man.now = Mock(return_value=fixed_now)
        nb_man.save = Mock()
        nb_man.pbar.close()
        nb_man.pbar = Mock()
        nb_man.cell_complete(cell)

        self.assertEqual(cell.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertIsNone(cell.metadata.papermill['duration'])
        self.assertFalse(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'], NotebookExecutionManager.COMPLETED)

        nb_man.save.assert_called_once()
        nb_man.pbar.update.assert_called_once()

    def test_cell_complete_after_cell_exception(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.notebook_start()
        cell = nb_man.nb.cells[0]
        nb_man.cell_start(cell)
        nb_man.cell_exception(cell)

        fixed_now = nb_man.now()

        nb_man.now = Mock(return_value=fixed_now)
        nb_man.save = Mock()
        nb_man.pbar.close()
        nb_man.pbar = Mock()
        nb_man.cell_complete(cell)

        self.assertIsNotNone(cell.metadata.papermill['start_time'])
        start_time = dateutil.parser.parse(cell.metadata.papermill['start_time'])

        self.assertEqual(cell.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertEqual(
            cell.metadata.papermill['duration'], (fixed_now - start_time).total_seconds()
        )
        self.assertTrue(cell.metadata.papermill['exception'])
        self.assertEqual(cell.metadata.papermill['status'], NotebookExecutionManager.FAILED)

        nb_man.save.assert_called_once()
        nb_man.pbar.update.assert_called_once()

    def test_cell_complete_new_nb(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.notebook_start()
        baz_nb = copy.deepcopy(nb_man.nb)
        baz_nb.metadata['baz'] = 'buz'
        nb_man.cell_complete(baz_nb.cells[0], nb=baz_nb)
        self.assertEqual(nb_man.nb.metadata['baz'], 'buz')

    def test_notebook_complete(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.notebook_start()

        fixed_now = nb_man.now()

        nb_man.now = Mock(return_value=fixed_now)
        nb_man.save = Mock()
        nb_man.pbar.close()
        nb_man.cleanup_pbar = Mock()

        nb_man.notebook_complete()

        self.assertIsNotNone(nb_man.nb.metadata.papermill['start_time'])
        start_time = dateutil.parser.parse(nb_man.nb.metadata.papermill['start_time'])

        self.assertEqual(nb_man.nb.metadata.papermill['end_time'], fixed_now.isoformat())
        self.assertEqual(
            nb_man.nb.metadata.papermill['duration'], (fixed_now - start_time).total_seconds()
        )
        self.assertFalse(nb_man.nb.metadata.papermill['exception'])

        nb_man.save.assert_called_once()
        nb_man.cleanup_pbar.assert_called_once()

    def test_notebook_complete_new_nb(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.notebook_start()
        baz_nb = copy.deepcopy(nb_man.nb)
        baz_nb.metadata['baz'] = 'buz'
        nb_man.notebook_complete(nb=baz_nb)
        self.assertEqual(nb_man.nb.metadata['baz'], 'buz')

    def test_notebook_complete_cell_status_completed(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.notebook_start()
        nb_man.notebook_complete()
        for cell in nb_man.nb.cells:
            self.assertEqual(cell.metadata.papermill['status'], NotebookExecutionManager.COMPLETED)

    def test_notebook_complete_cell_status_with_failed(self):
        nb_man = NotebookExecutionManager(self.nb)
        nb_man.notebook_start()
        nb_man.cell_exception(nb_man.nb.cells[1])
        nb_man.notebook_complete()
        self.assertEqual(
            nb_man.nb.cells[0].metadata.papermill['status'], NotebookExecutionManager.COMPLETED
        )
        self.assertEqual(
            nb_man.nb.cells[1].metadata.papermill['status'], NotebookExecutionManager.FAILED
        )
        for cell in nb_man.nb.cells[2:]:
            self.assertEqual(cell.metadata.papermill['status'], NotebookExecutionManager.PENDING)


class TestEngineBase(unittest.TestCase):
    def setUp(self):
        self.notebook_name = 'simple_execute.ipynb'
        self.notebook_path = get_notebook_path(self.notebook_name)
        self.nb = load_notebook_node(self.notebook_path)

    def test_wrap_and_execute_notebook(self):
        '''
        Mocks each wrapped call and proves the correct inputs get applies to
        the correct underlying calls for execute_notebook.
        '''
        with patch.object(Engine, 'execute_managed_notebook') as exec_mock:
            with patch.object(engines, 'NotebookExecutionManager') as wrap_mock:
                Engine.execute_notebook(
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
        class CellCallbackEngine(Engine):
            @classmethod
            def execute_managed_notebook(cls, nb_man, kernel_name, **kwargs):
                for cell in nb_man.nb.cells:
                    nb_man.cell_start(cell)
                    nb_man.cell_complete(cell)

        with patch.object(NotebookExecutionManager, 'save') as save_mock:
            nb = CellCallbackEngine.execute_notebook(self.nb, 'python', output_path='foo.ipynb')

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
                self.assertEqual(
                    cell.metadata.papermill['status'], NotebookExecutionManager.COMPLETED
                )

    def test_no_cell_callback_execute(self):
        class NoCellCallbackEngine(Engine):
            @classmethod
            def execute_managed_notebook(cls, nb_man, kernel_name, **kwargs):
                pass

        with patch.object(NotebookExecutionManager, 'save') as save_mock:
            with patch.object(NotebookExecutionManager, 'complete_pbar') as pbar_comp_mock:
                nb = NoCellCallbackEngine.execute_notebook(
                    self.nb, 'python', output_path='foo.ipynb'
                )

                self.assertEqual(nb, AnyMock(NotebookNode))
                self.assertNotEqual(self.nb, nb)

                self.assertEqual(save_mock.call_count, 2)
                pbar_comp_mock.assert_called_once()

                self.assertIsNotNone(nb.metadata.papermill['start_time'])
                self.assertIsNotNone(nb.metadata.papermill['end_time'])
                self.assertEqual(nb.metadata.papermill['duration'], AnyMock(float))
                self.assertFalse(nb.metadata.papermill['exception'])

                for cell in nb.cells:
                    self.assertIsNone(cell.metadata.papermill['start_time'])
                    self.assertIsNone(cell.metadata.papermill['end_time'])
                    self.assertIsNone(cell.metadata.papermill['duration'])
                    self.assertIsNone(cell.metadata.papermill['exception'])
                    self.assertEqual(
                        cell.metadata.papermill['status'], NotebookExecutionManager.COMPLETED
                    )


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

            with patch.object(NotebookExecutionManager, 'save') as save_mock:
                nb = NBConvertEngine.execute_notebook(
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
                    timeout=1000, startup_timeout=30, kernel_name='python', log=logger
                )
                log_out_mock.assert_called_once_with(True)
                pep_mock.return_value.preprocess.assert_called_once_with(
                    AnyMock(NotebookExecutionManager), {'bar': 'baz'}
                )
                # Once for start and once for complete (cell not called by mock)
                self.assertEqual(save_mock.call_count, 2)

    def test_nb_convert_engine_execute(self):
        with patch.object(NotebookExecutionManager, 'save') as save_mock:
            nb = NBConvertEngine.execute_notebook(
                self.nb, 'python', output_path='foo.ipynb', progress_bar=False, log_output=True
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
                self.assertEqual(
                    cell.metadata.papermill['status'], NotebookExecutionManager.COMPLETED
                )

    def test_nb_convert_log_outputs(self):
        with patch.object(logger, 'info') as info_mock:
            with patch.object(logger, 'warning') as warning_mock:
                with patch.object(NotebookExecutionManager, 'save'):
                    NBConvertEngine.execute_notebook(
                        self.nb,
                        'python',
                        output_path='foo.ipynb',
                        progress_bar=False,
                        log_output=True,
                    )
                    info_mock.assert_has_calls(
                        [
                            call('Executing notebook with kernel: python'),
                            call('Executing Cell 1---------------------------------------'),
                            call('Ending Cell 1------------------------------------------'),
                            call('Executing Cell 2---------------------------------------'),
                            call('None\n'),
                            call('Ending Cell 2------------------------------------------'),
                        ]
                    )
                    warning_mock.is_not_called()

    def test_nb_convert_no_log_outputs(self):
        with patch.object(logger, 'info') as info_mock:
            with patch.object(logger, 'warning') as warning_mock:
                with patch.object(NotebookExecutionManager, 'save'):
                    NBConvertEngine.execute_notebook(
                        self.nb,
                        'python',
                        output_path='foo.ipynb',
                        progress_bar=False,
                        log_output=False,
                    )
                    info_mock.is_not_called()
                    warning_mock.is_not_called()


class TestEngineRegistration(unittest.TestCase):
    def setUp(self):
        self.papermill_engines = engines.PapermillEngines()

    def test_registration(self):
        mock_engine = Mock()
        self.papermill_engines.register("mock_engine", mock_engine)
        self.assertIn("mock_engine", self.papermill_engines._engines)
        self.assertIs(mock_engine, self.papermill_engines._engines["mock_engine"])

    def test_getting(self):
        mock_engine = Mock()
        self.papermill_engines.register("mock_engine", mock_engine)
        # test retrieving an engine works
        retrieved_engine = self.papermill_engines.get_engine("mock_engine")
        self.assertIs(mock_engine, retrieved_engine)
        # test you can't retrieve a non-registered engine
        self.assertRaises(
            exceptions.PapermillException, self.papermill_engines.get_engine, "non-existent"
        )

    def test_registering_entry_points(self):
        fake_entrypoint = Mock(load=Mock())
        fake_entrypoint.name = "fake-engine"

        with patch(
            "entrypoints.get_group_all", return_value=[fake_entrypoint]
        ) as mock_get_group_all:

            self.papermill_engines.register_entry_points()
            mock_get_group_all.assert_called_once_with("papermill.engine")
            self.assertEqual(
                self.papermill_engines.get_engine("fake-engine"), fake_entrypoint.load.return_value
            )
