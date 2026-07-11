import unittest
from contextlib import contextmanager
from io import StringIO
from unittest.mock import call, patch

import nbformat

from ..clientwrap import PapermillNotebookClient
from ..engines import NotebookExecutionManager
from ..log import logger
from . import get_notebook_path


class TestPapermillClientWrapper(unittest.TestCase):
    def setUp(self):
        self.nb = nbformat.read(get_notebook_path('test_logging.ipynb'), as_version=4)
        self.nb_man = NotebookExecutionManager(self.nb)
        self.client = PapermillNotebookClient(self.nb_man, log=logger, log_output=True)

    def test_logging_stderr_msg(self):
        with patch.object(logger, 'warning') as warning_mock:
            for output in self.nb.cells[0].get("outputs", []):
                self.client.log_output_message(output)
            warning_mock.assert_called_once_with("INFO:test:test text\n")

    def test_logging_stdout_msg(self):
        with patch.object(logger, 'info') as info_mock:
            for output in self.nb.cells[1].get("outputs", []):
                self.client.log_output_message(output)
            info_mock.assert_called_once_with("hello world\n")

    def test_logging_data_msg(self):
        with patch.object(logger, 'info') as info_mock:
            for output in self.nb.cells[2].get("outputs", []):
                self.client.log_output_message(output)
            info_mock.assert_has_calls(
                [
                    call("<matplotlib.axes._subplots.AxesSubplot at 0x7f8391f10290>"),
                    call("<matplotlib.figure.Figure at 0x7f830af7b350>"),
                ]
            )

    def test_kernel_startup_stdout_does_not_leak_to_parent_stdout(self):
        @contextmanager
        def noisy_kernel_setup(**kwargs):
            print("Starting kernel...")
            yield

        self.client.kc = unittest.mock.Mock()
        self.client.kc.kernel_info.return_value = 'kernel-info'

        with (
            patch.object(self.client, 'setup_kernel', noisy_kernel_setup),
            patch.object(self.client, 'papermill_execute_cells'),
            patch.object(self.client, 'wait_for_reply', return_value={'content': {'language_info': {}}}),
            patch.object(self.client, 'set_widgets_metadata'),
            patch('sys.stdout', new_callable=StringIO) as stdout,
        ):
            self.client.execute()

        self.assertEqual(stdout.getvalue(), "")
