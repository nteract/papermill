import unittest
from gcsfs.utils import HtmlError as RateLimitException
from ..iorw import GCSHandler
from retry.api import retry_call
import six

if six.PY3:
    from unittest.mock import patch
else:
    from mock import patch

_RETRIES = 3


class MockGCSFileSystem(object):
    def __init__(self):
        self._file = MockGCSFile()

    def open(self, *args, **kwargs):
        return self._file

    def ls(self, *args, **kwargs):
        return []


class MockGCSFile(object):
    def __init__(self):
        self.write_count = 0

    def __enter__(self):
        self._value = 'default value'
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def read(self):
        return self._value

    def write(self, buf):
        self.write_count += 1
        if buf == 'raise_limit_exception':
            raise RateLimitException
        elif buf == 'retry':
            if self.write_count < _RETRIES:
                raise RateLimitException
            else:
                return self.write_count
        else:
            pass


class GCSTest(unittest.TestCase):
    """Tests for `GCS`."""

    def setUp(self):
        self.gcs_handler = GCSHandler()

    @patch('papermill.iorw.GCSFileSystem', side_effect=MockGCSFileSystem)
    def test_gcs_read(self, mock_gcs_filesystem):
        client = self.gcs_handler._get_client()
        assert self.gcs_handler.read(
            'gs://bucket/test.ipynb') == 'default value'
        # Check that client is only generated once
        self.assertIs(client, self.gcs_handler._get_client())

    @patch('papermill.iorw.GCSFileSystem', side_effect=MockGCSFileSystem)
    def test_gcs_write(self, mock_gcs_filesystem):
        client = self.gcs_handler._get_client()
        self.gcs_handler.write('new value', 'gs://bucket/test.ipynb')
        # Check that client is only generated once
        self.assertIs(client, self.gcs_handler._get_client())

    @patch('papermill.iorw.GCSFileSystem', side_effect=MockGCSFileSystem)
    def test_gcs_listdir(self, mock_gcs_filesystem):
        client = self.gcs_handler._get_client()
        self.gcs_handler.listdir('testdir')
        # Check that client is only generated once
        self.assertIs(client, self.gcs_handler._get_client())

    @patch('papermill.iorw.GCSFileSystem', side_effect=MockGCSFileSystem)
    def test_gcs_handle_exception(self, mock_gcs_filesystem):
        with self.assertRaises(RateLimitException):
            retry_call(
                self.gcs_handler.write,
                exceptions=RateLimitException,
                fargs=['raise_limit_exception', 'gs://bucket/test.ipynb'],
                tries=_RETRIES,
                delay=1,
                backoff=1,
                max_delay=2)

    @patch('papermill.iorw.GCSFileSystem', side_effect=MockGCSFileSystem)
    def test_gcs_retry(self, mock_gcs_filesystem):
        write_count = retry_call(
            self.gcs_handler.write,
            exceptions=RateLimitException,
            fargs=['retry', 'gs://bucket/test.ipynb'],
            tries=_RETRIES,
            delay=1,
            backoff=1,
            max_delay=2)
        self.assertEqual(write_count, _RETRIES)
