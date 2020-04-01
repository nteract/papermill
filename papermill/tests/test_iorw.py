# -*- coding: utf-8 -*-

import json
import unittest
import os
import io
import nbformat
import pytest

from requests.exceptions import ConnectionError
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from .. import iorw
from ..iorw import (
    HttpHandler,
    LocalHandler,
    ADLHandler,
    PapermillIO,
    read_yaml_file,
    papermill_io,
    local_file_io_cwd,
)
from ..exceptions import PapermillException

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestPapermillIO(unittest.TestCase):
    """
    Tests for `PapermillIO`.
    """

    class FakeHandler(object):
        def __init__(self, ver):
            self.ver = ver

        def read(self, path):
            return "contents from {} for version {}".format(path, self.ver)

        def listdir(self, path):
            return ["fake", "contents"]

        def write(self, buf, path):
            return "wrote {}".format(buf)

        def pretty_path(self, path):
            return "{}/pretty/{}".format(path, self.ver)

    class FakeByteHandler(object):
        def __init__(self, ver):
            self.ver = ver

        def read(self, path):
            local_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(local_dir, path)) as f:
                return f.read()

        def listdir(self, path):
            return ["fake", "contents"]

        def write(self, buf, path):
            return "wrote {}".format(buf)

        def pretty_path(self, path):
            return "{}/pretty/{}".format(path, self.ver)

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

    def test_entrypoint_register(self):

        fake_entrypoint = Mock(load=Mock())
        fake_entrypoint.name = "fake-from-entry-point://"

        with patch(
            "entrypoints.get_group_all", return_value=[fake_entrypoint]
        ) as mock_get_group_all:

            self.papermill_io.register_entry_points()
            mock_get_group_all.assert_called_once_with("papermill.io")
            assert (
                self.papermill_io.get_handler("fake-from-entry-point://")
                == fake_entrypoint.load.return_value
            )

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
        self.assertEqual(
            self.papermill_io.read("fake/path"), "contents from fake/path for version 1"
        )

    def test_read_bytes(self):
        self.assertIsNotNone(
            self.papermill_io_bytes.read("notebooks/gcs/gcs_in/gcs-simple_notebook.ipynb")
        )

    def test_read_with_no_file_extension(self):
        with pytest.warns(UserWarning):
            self.papermill_io.read("fake/path")

    def test_read_with_invalid_file_extension(self):
        with pytest.warns(UserWarning):
            self.papermill_io.read("fake/path/fakeinputpath.ipynb1")

    def test_read_with_valid_file_extension(self):
        with pytest.warns(None) as warns:
            self.papermill_io.read("fake/path/fakeinputpath.ipynb")
        self.assertEqual(len(warns), 0)

    def test_read_yaml_with_no_file_extension(self):
        with pytest.warns(UserWarning):
            read_yaml_file("fake/path")

    def test_read_yaml_with_invalid_file_extension(self):
        with pytest.warns(UserWarning):
            read_yaml_file("fake/path/fakeinputpath.ipynb")

    def test_read_stdin(self):
        file_content = u'Τὴ γλῶσσα μοῦ ἔδωσαν ἑλληνικὴ'
        with patch('sys.stdin', io.StringIO(file_content)):
            self.assertEqual(self.papermill_io.read("-"), file_content)

    def test_listdir(self):
        self.assertEqual(self.papermill_io.listdir("fake/path"), ["fake", "contents"])

    def test_write(self):
        self.assertEqual(self.papermill_io.write("buffer", "fake/path"), "wrote buffer")

    def test_write_with_no_file_extension(self):
        with pytest.warns(UserWarning):
            self.papermill_io.write("buffer", "fake/path")

    def test_write_with_invalid_file_extension(self):
        with pytest.warns(UserWarning):
            self.papermill_io.write("buffer", "fake/path/fakeoutputpath.ipynb1")

    def test_write_stdout(self):
        file_content = u'Τὴ γλῶσσα μοῦ ἔδωσαν ἑλληνικὴ'
        out = io.BytesIO()
        with patch('sys.stdout', out):
            self.papermill_io.write(file_content, "-")
            self.assertEqual(out.getvalue(), file_content.encode('utf-8'))

    def test_pretty_path(self):
        self.assertEqual(self.papermill_io.pretty_path("fake/path"), "fake/path/pretty/1")


class TestLocalHandler(unittest.TestCase):
    """
    Tests for `LocalHandler`
    """

    def test_read_utf8(self):
        self.assertEqual(LocalHandler().read(os.path.join(FIXTURE_PATH, 'rock.txt')).strip(), u'✄')

    def test_write_utf8(self):
        with TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, 'paper.txt')
            LocalHandler().write(u'✄', path)
            with io.open(path, 'r', encoding='utf-8') as f:
                self.assertEqual(f.read().strip(), u'✄')

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
            handler.write(u'✄', 'paper.txt')

            path = os.path.join(temp_dir, 'paper.txt')
            with io.open(path, 'r', encoding='utf-8') as f:
                self.assertEqual(f.read().strip(), u'✄')

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
                    local_handler.write(u'✄', 'paper.txt')
                    self.assertEqual(local_handler.read('paper.txt'), u'✄')

                # Double check it used the tmpdir
                path = os.path.join(temp_dir, 'paper.txt')
                with io.open(path, 'r', encoding='utf-8') as f:
                    self.assertEqual(f.read().strip(), u'✄')
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

        self.assertEqual('{}'.format(e.exception), 'listdir is not supported by HttpHandler')

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
