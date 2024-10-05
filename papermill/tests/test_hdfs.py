import unittest
from unittest.mock import MagicMock, patch

import pytest

from ..iorw import HDFSHandler


class MockHadoopFileSystem(MagicMock):
    def get_file_info(self, path):
        return [MockFileInfo('test1.ipynb'), MockFileInfo('test2.ipynb')]

    def open_input_stream(self, path):
        return MockHadoopFile()

    def open_output_stream(self, path):
        return MockHadoopFile()


class MockHadoopFile:
    def __init__(self):
        self._content = b'Content of notebook'

    def __enter__(self, *args):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self._content

    def write(self, new_content):
        self._content = new_content
        return 1


class MockFileInfo:
    def __init__(self, path):
        self.path = path


@pytest.mark.skip(reason="No valid dep package for python 3.12 yet")
@patch('papermill.iorw.HadoopFileSystem', side_effect=MockHadoopFileSystem())
class HDFSTest(unittest.TestCase):
    def setUp(self):
        self.hdfs_handler = HDFSHandler()

    def test_hdfs_listdir(self, mock_hdfs_filesystem):
        client = self.hdfs_handler._get_client()
        self.assertEqual(self.hdfs_handler.listdir("hdfs:///Projects/"), ['test1.ipynb', 'test2.ipynb'])
        # Check if client is the same after calling
        self.assertIs(client, self.hdfs_handler._get_client())

    def test_hdfs_read(self, mock_hdfs_filesystem):
        client = self.hdfs_handler._get_client()
        self.assertEqual(self.hdfs_handler.read("hdfs:///Projects/test1.ipynb"), b'Content of notebook')
        self.assertIs(client, self.hdfs_handler._get_client())

    def test_hdfs_write(self, mock_hdfs_filesystem):
        client = self.hdfs_handler._get_client()
        self.assertEqual(self.hdfs_handler.write("hdfs:///Projects/test1.ipynb", b'New content'), 1)
        self.assertIs(client, self.hdfs_handler._get_client())
