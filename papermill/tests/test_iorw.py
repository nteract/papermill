import io
import json
import os
import unittest
import warnings
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import nbformat
import pytest
from requests.exceptions import ConnectionError

from .. import iorw
from ..exceptions import PapermillException
from ..iorw import (
    ADLHandler,
    HttpHandler,
    LocalHandler,
    NoIOHandler,
    NotebookNodeHandler,
    PapermillIO,
    StreamHandler,
    local_file_io_cwd,
    papermill_io,
    read_yaml_file,
)
from . import get_notebook_path

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestPapermillIO(unittest.TestCase):
    """
    Tests for `PapermillIO`.
    """

    class FakeHandler:
        def __init__(self, ver):
            self.ver = ver

        def read(self, path):
            return f"contents from {path} for version {self.ver}"

        def listdir(self, path):
            return ["fake", "contents"]

        def write(self, buf, path):
            return f"wrote {buf}"

        def pretty_path(self, path):
            return f"{path}/pretty/{self.ver}"

    class FakeByteHandler:
        def __init__(self, ver):
            self.ver = ver

        def read(self, path):
            local_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(local_dir, path)) as f:
                return f.read()

        def listdir(self, path):
            return ["fake", "contents"]

        def write(self, buf, path):
            return f"wrote {buf}"

        def pretty_path(self, path):
            return f"{path}/pretty/{self.ver}"

    def setUp(self):
        self.papermill_io = PapermillIO()
        self.papermill_io_bytes = PapermillIO()
        self.fake1 = self.FakeHandler(1)
        self.fake2 = self.FakeHandler(2)
        self.fake_byte1 = self.FakeByteHandler(1)
        self.papermill_io.register("fake", self.fake1)
        self.papermill_io_bytes.register("notebooks", self.fake_byte1)

        self.old_papermill_io = iorw.papermill_io
        iorw.papermill_io = self.papermill_io

    def tearDown(self):
        iorw.papermill_io = self.old_papermill_io

    def test_get_handler(self):
        self.assertEqual(self.papermill_io.get_handler("fake"), self.fake1)

    def test_get_local_handler(self):
        with self.assertRaises(PapermillException):
            self.papermill_io.get_handler("dne")

        self.papermill_io.register("local", self.fake2)
        self.assertEqual(self.papermill_io.get_handler("dne"), self.fake2)

    def test_get_no_io_handler(self):
        self.assertIsInstance(self.papermill_io.get_handler(None), NoIOHandler)

    def test_get_notebook_node_handler(self):
        test_nb = nbformat.read(get_notebook_path('test_notebooknode_io.ipynb'), as_version=4)
        self.assertIsInstance(self.papermill_io.get_handler(test_nb), NotebookNodeHandler)

    def test_entrypoint_register(self):
        fake_entrypoint = Mock(load=Mock())
        fake_entrypoint.name = "fake-from-entry-point://"

        with patch("entrypoints.get_group_all", return_value=[fake_entrypoint]) as mock_get_group_all:
            self.papermill_io.register_entry_points()
            mock_get_group_all.assert_called_once_with("papermill.io")
            fake_ = self.papermill_io.get_handler("fake-from-entry-point://")
            assert fake_ == fake_entrypoint.load.return_value

    def test_register_ordering(self):
        # Should match fake1 with fake2 path
        self.assertEqual(self.papermill_io.get_handler("fake2/path"), self.fake1)

        self.papermill_io.reset()
        self.papermill_io.register("fake", self.fake1)
        self.papermill_io.register("fake2", self.fake2)

        # Should match fake1 with fake1 path, and NOT fake2 path/match
        self.assertEqual(self.papermill_io.get_handler("fake/path"), self.fake1)
        # Should match fake2 with fake2 path
        self.assertEqual(self.papermill_io.get_handler("fake2/path"), self.fake2)

    def test_read(self):
        self.assertEqual(self.papermill_io.read("fake/path"), "contents from fake/path for version 1")

    def test_read_bytes(self):
        self.assertIsNotNone(self.papermill_io_bytes.read("notebooks/gcs/gcs_in/gcs-simple_notebook.ipynb"))

    def test_read_with_no_file_extension(self):
        with pytest.warns(UserWarning):
            self.papermill_io.read("fake/path")

    def test_read_with_invalid_file_extension(self):
        with pytest.warns(UserWarning):
            self.papermill_io.read("fake/path/fakeinputpath.ipynb1")

    def test_read_with_valid_file_extension(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self.papermill_io.read("fake/path/fakeinputpath.ipynb")

    def test_read_yaml_with_no_file_extension(self):
        with pytest.warns(UserWarning):
            read_yaml_file("fake/path")

    def test_read_yaml_with_invalid_file_extension(self):
        with pytest.warns(UserWarning):
            read_yaml_file("fake/path/fakeinputpath.ipynb")

    def test_read_stdin(self):
        file_content = 'Τὴ γλῶσσα μοῦ ἔδωσαν ἑλληνικὴ'
        with patch('sys.stdin', io.StringIO(file_content)):
            self.assertEqual(self.old_papermill_io.read("-"), file_content)

    def test_listdir(self):
        self.assertEqual(self.papermill_io.listdir("fake/path"), ["fake", "contents"])

    def test_write(self):
        self.assertEqual(self.papermill_io.write("buffer", "fake/path"), "wrote buffer")

    def test_write_with_no_file_extension(self):
        with pytest.warns(UserWarning):
            self.papermill_io.write("buffer", "fake/path")

    def test_write_with_path_of_none(self):
        self.assertIsNone(self.papermill_io.write('buffer', None))

    def test_write_with_invalid_file_extension(self):
        with pytest.warns(UserWarning):
            self.papermill_io.write("buffer", "fake/path/fakeoutputpath.ipynb1")

    def test_write_stdout(self):
        file_content = 'Τὴ γλῶσσα μοῦ ἔδωσαν ἑλληνικὴ'
        out = io.BytesIO()
        with patch('sys.stdout', out):
            self.old_papermill_io.write(file_content, "-")
            self.assertEqual(out.getvalue(), file_content.encode('utf-8'))

    def test_pretty_path(self):
        self.assertEqual(self.papermill_io.pretty_path("fake/path"), "fake/path/pretty/1")


class TestLocalHandler(unittest.TestCase):
    """
    Tests for `LocalHandler`
    """

    def test_read_utf8(self):
        self.assertEqual(LocalHandler().read(os.path.join(FIXTURE_PATH, 'rock.txt')).strip(), '✄')

    def test_write_utf8(self):
        with TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, 'paper.txt')
            LocalHandler().write('✄', path)
            with open(path, encoding='utf-8') as f:
                self.assertEqual(f.read().strip(), '✄')

    def test_write_no_directory_exists(self):
        with self.assertRaises(FileNotFoundError):
            LocalHandler().write("buffer", "fake/path/fakenb.ipynb")

    def test_write_local_directory(self):
        with patch.object(io, 'open'):
            # Shouldn't raise with missing directory
            LocalHandler().write("buffer", "local.ipynb")

    def test_write_passed_cwd(self):
        with TemporaryDirectory() as temp_dir:
            handler = LocalHandler()

            handler.cwd(temp_dir)
            handler.write('✄', 'paper.txt')

            path = os.path.join(temp_dir, 'paper.txt')
            with open(path, encoding='utf-8') as f:
                self.assertEqual(f.read().strip(), '✄')

    def test_local_file_io_cwd(self):
        with TemporaryDirectory() as temp_dir:
            # Some internal model fixing to avoid side-effecting anything else that
            # reads from the module global defaults
            handlers = papermill_io._handlers
            try:
                local_handler = LocalHandler()
                papermill_io.reset()
                papermill_io.register("local", local_handler)

                with local_file_io_cwd(temp_dir):
                    local_handler.write('✄', 'paper.txt')
                    self.assertEqual(local_handler.read('paper.txt'), '✄')

                # Double check it used the tmpdir
                path = os.path.join(temp_dir, 'paper.txt')
                with open(path, encoding='utf-8') as f:
                    self.assertEqual(f.read().strip(), '✄')
            finally:
                papermill_io.handlers = handlers

    def test_read_from_string(self):
        nbnode_as_string = nbformat.writes(nbformat.v4.new_notebook())
        # the stringified notebook is passed straight through
        self.assertEqual(LocalHandler().read(nbnode_as_string), nbnode_as_string)

    def test_invalid_string(self):
        # a string from which we can't extract a notebook is assumed to
        # be a file and an IOError will be raised
        with self.assertRaises(IOError):
            LocalHandler().read("a random string")


class TestNoIOHandler(unittest.TestCase):
    def test_raises_on_read(self):
        with self.assertRaises(PapermillException):
            NoIOHandler().read(None)

    def test_raises_on_listdir(self):
        with self.assertRaises(PapermillException):
            NoIOHandler().listdir(None)

    def test_write_returns_none(self):
        self.assertIsNone(NoIOHandler().write('buf', None))

    def test_pretty_path(self):
        expect = 'Notebook will not be saved'
        self.assertEqual(NoIOHandler().pretty_path(None), expect)


class TestADLHandler(unittest.TestCase):
    """
    Tests for `ADLHandler`
    """

    def setUp(self):
        self.handler = ADLHandler()
        self.handler._client = Mock(
            read=Mock(return_value=["foo", "bar", "baz"]),
            listdir=Mock(return_value=["foo", "bar", "baz"]),
            write=Mock(),
        )

    def test_read(self):
        self.assertEqual(self.handler.read("some_path"), "foo\nbar\nbaz")

    def test_listdir(self):
        self.assertEqual(self.handler.listdir("some_path"), ["foo", "bar", "baz"])

    def test_write(self):
        self.handler.write("foo", "bar")
        self.handler._client.write.assert_called_once_with("foo", "bar")


class TestHttpHandler(unittest.TestCase):
    """
    Tests for `HttpHandler`.
    """

    def test_listdir(self):
        """
        Tests that listdir raises `PapermillException` saying that that
        `listdir` function is not supported.
        """
        with self.assertRaises(PapermillException) as e:
            HttpHandler.listdir('http://example.com')

        self.assertEqual(f'{e.exception}', 'listdir is not supported by HttpHandler')

    def test_read(self):
        """
        Tests that the `read` function performs a request to the giving path
        and returns the response.
        """
        path = 'http://example.com'
        text = 'request test response'

        with patch('papermill.iorw.requests.get') as mock_get:
            mock_get.return_value = Mock(text=text)
            self.assertEqual(HttpHandler.read(path), text)
            mock_get.assert_called_once_with(path, headers={'Accept': 'application/json'})

    def test_write(self):
        """
        Tests that the `write` function performs a put request to the given
        path.
        """
        path = 'http://example.com'
        buf = '{"papermill": true}'

        with patch('papermill.iorw.requests.put') as mock_put:
            HttpHandler.write(buf, path)
            mock_put.assert_called_once_with(path, json=json.loads(buf))

    def test_write_failure(self):
        """
        Tests that the `write` function raises on failure to put the buffer.
        """
        path = 'http://localhost:9999'
        buf = '{"papermill": true}'

        with self.assertRaises(ConnectionError):
            HttpHandler.write(buf, path)


class TestStreamHandler(unittest.TestCase):
    @patch('sys.stdin', io.StringIO('mock stream'))
    def test_read_from_stdin(self):
        result = StreamHandler().read('foo')
        self.assertEqual(result, 'mock stream')

    def test_raises_on_listdir(self):
        with self.assertRaises(PapermillException):
            StreamHandler().listdir(None)

    @patch('sys.stdout')
    def test_write_to_stdout_buffer(self, mock_stdout):
        mock_stdout.buffer = io.BytesIO()
        StreamHandler().write('mock stream', 'foo')
        self.assertEqual(mock_stdout.buffer.getbuffer(), b'mock stream')

    @patch('sys.stdout', new_callable=io.BytesIO)
    def test_write_to_stdout(self, mock_stdout):
        StreamHandler().write('mock stream', 'foo')
        self.assertEqual(mock_stdout.getbuffer(), b'mock stream')

    def test_pretty_path_returns_input_path(self):
        '''Should return the input str, which often is the default registered schema "-"'''
        self.assertEqual(StreamHandler().pretty_path('foo'), 'foo')


class TestNotebookNodeHandler(unittest.TestCase):
    def test_read_notebook_node(self):
        input_nb = nbformat.read(get_notebook_path('test_notebooknode_io.ipynb'), as_version=4)
        result = NotebookNodeHandler().read(input_nb)
        expect = (
            '{\n "cells": [\n  {\n   "cell_type": "code",\n   "execution_count": null,'
            '\n   "metadata": {},\n   "outputs": [],\n   "source": ['
            '\n    "print(\'Hello World\')"\n   ]\n  }\n ],\n "metadata": {'
            '\n  "kernelspec": {\n   "display_name": "Python 3",\n   "language": "python",'
            '\n   "name": "python3"\n  }\n },\n "nbformat": 4,\n "nbformat_minor": 2\n}'
        )
        self.assertEqual(result, expect)

    def test_raises_on_listdir(self):
        with self.assertRaises(PapermillException):
            NotebookNodeHandler().listdir('foo')

    def test_raises_on_write(self):
        with self.assertRaises(PapermillException):
            NotebookNodeHandler().write('foo', 'bar')

    def test_pretty_path(self):
        expect = 'NotebookNode object'
        self.assertEqual(NotebookNodeHandler().pretty_path('foo'), expect)
