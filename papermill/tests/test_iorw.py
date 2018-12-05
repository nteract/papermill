# -*- coding: utf-8 -*-

import json
import unittest
import os
import io
import tempfile
import pytest
from requests.exceptions import ConnectionError

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

from ..exceptions import PapermillException
from ..iorw import HttpHandler, LocalHandler, ADLHandler, PapermillIO

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

    def setUp(self):
        self.papermill_io = PapermillIO()
        self.fake1 = self.FakeHandler(1)
        self.fake2 = self.FakeHandler(2)
        self.papermill_io.register("fake", self.fake1)

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
            for scheme, handler in self.papermill_io._handlers:
                print(scheme, handler)
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

    def test_read_with_no_file_extension(self):
        with pytest.warns(UserWarning):
            self.papermill_io.read("fake/path")

    def test_read_with_invalid_file_extension(self):
        with pytest.warns(UserWarning):
            self.papermill_io.read("fake/path/fakeinputpath.ipynb1")

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

    def test_pretty_path(self):
        self.assertEqual(self.papermill_io.pretty_path("fake/path"), "fake/path/pretty/1")


class TestLocalHandler(unittest.TestCase):
    """
    Tests for `LocalHandler`
    """

    def test_read_utf8(self):
        self.assertEqual(LocalHandler.read(os.path.join(FIXTURE_PATH, 'rock.txt')).strip(), u'✄')

    def test_write_utf8(self):
        path = os.path.join(tempfile.mkdtemp(), 'paper.txt')
        LocalHandler.write(u'✄', path)
        with io.open(path, 'r', encoding='utf-8') as f:
            self.assertEqual(f.read().strip(), u'✄')

    def test_write_no_directory_exists(self):
        with self.assertRaises(FileNotFoundError):
            LocalHandler.write("buffer", "fake/path/fakenb.ipynb")

    def test_write_local_directory(self):
        with patch.object(io, 'open'):
            # Shouldn't raise with missing directory
            LocalHandler.write("buffer", "local.ipynb")


class TestADLHandler(unittest.TestCase):
    """
    Tests for `ADLHandler`
    """

    def setUp(self):
        self.old_client = ADLHandler._client
        self.mock_client = Mock(
            read=Mock(return_value=["foo", "bar", "baz"]),
            listdir=Mock(return_value=["foo", "bar", "baz"]),
            write=Mock(),
        )
        ADLHandler._client = self.mock_client

    def tearDown(self):
        ADLHandler._client = self.old_client

    def test_read(self):
        self.assertEqual(ADLHandler.read("some_path"), "foo\nbar\nbaz")

    def test_listdir(self):
        self.assertEqual(ADLHandler.listdir("some_path"), ["foo", "bar", "baz"])

    def test_write(self):
        ADLHandler.write("foo", "bar")
        self.mock_client.write.assert_called_once_with("foo", "bar")


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
