import unittest

from unittest.mock import patch

from ..exceptions import PapermillRateLimitException
from ..iorw import GCSHandler, fallback_gs_is_retriable

try:
    try:
        from gcsfs.utils import HttpError as GCSHttpError
    except ImportError:
        from gcsfs.utils import HtmlError as GCSHttpError
except ImportError:
    # Fall back to a sane import if gcsfs is missing
    GCSHttpError = Exception

try:
    from gcsfs.utils import RateLimitException as GCSRateLimitException
except ImportError:
    # Fall back to GCSHttpError when using older library
    GCSRateLimitException = GCSHttpError


def mock_gcs_fs_wrapper(exception=None, max_raises=1):
    class MockGCSFileSystem(object):
        def __init__(self):
            self._file = MockGCSFile(exception, max_raises)

        def open(self, *args, **kwargs):
            return self._file

        def ls(self, *args, **kwargs):
            return []

    return MockGCSFileSystem


class MockGCSFile(object):
    def __init__(self, exception=None, max_raises=1):
        self.read_count = 0
        self.write_count = 0
        self.exception = exception
        self.max_raises = max_raises

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def read(self):
        self.read_count += 1
        if self.exception and self.read_count <= self.max_raises:
            raise self.exception
        return self.read_count

    def write(self, buf):
        self.write_count += 1
        if self.exception and self.write_count <= self.max_raises:
            raise self.exception
        return self.write_count


class GCSTest(unittest.TestCase):
    """Tests for `GCS`."""

    def setUp(self):
        self.gcs_handler = GCSHandler()

    @patch('papermill.iorw.GCSFileSystem', side_effect=mock_gcs_fs_wrapper())
    def test_gcs_read(self, mock_gcs_filesystem):
        client = self.gcs_handler._get_client()
        self.assertEqual(self.gcs_handler.read('gs://bucket/test.ipynb'), 1)
        # Check that client is only generated once
        self.assertIs(client, self.gcs_handler._get_client())

    @patch('papermill.iorw.GCSFileSystem', side_effect=mock_gcs_fs_wrapper())
    def test_gcs_write(self, mock_gcs_filesystem):
        client = self.gcs_handler._get_client()
        self.assertEqual(self.gcs_handler.write('new value', 'gs://bucket/test.ipynb'), 1)
        # Check that client is only generated once
        self.assertIs(client, self.gcs_handler._get_client())

    @patch('papermill.iorw.GCSFileSystem', side_effect=mock_gcs_fs_wrapper())
    def test_gcs_listdir(self, mock_gcs_filesystem):
        client = self.gcs_handler._get_client()
        self.gcs_handler.listdir('testdir')
        # Check that client is only generated once
        self.assertIs(client, self.gcs_handler._get_client())

    @patch(
        'papermill.iorw.GCSFileSystem',
        side_effect=mock_gcs_fs_wrapper(
            GCSRateLimitException({"message": "test", "code": 429}), 10
        ),
    )
    def test_gcs_handle_exception(self, mock_gcs_filesystem):
        with patch.object(GCSHandler, 'RETRY_DELAY', 0):
            with patch.object(GCSHandler, 'RETRY_MULTIPLIER', 0):
                with patch.object(GCSHandler, 'RETRY_MAX_DELAY', 0):
                    with self.assertRaises(PapermillRateLimitException):
                        self.gcs_handler.write('raise_limit_exception', 'gs://bucket/test.ipynb')

    @patch(
        'papermill.iorw.GCSFileSystem',
        side_effect=mock_gcs_fs_wrapper(GCSRateLimitException({"message": "test", "code": 429}), 1),
    )
    def test_gcs_retry(self, mock_gcs_filesystem):
        with patch.object(GCSHandler, 'RETRY_DELAY', 0):
            with patch.object(GCSHandler, 'RETRY_MULTIPLIER', 0):
                with patch.object(GCSHandler, 'RETRY_MAX_DELAY', 0):
                    self.assertEqual(
                        self.gcs_handler.write('raise_limit_exception', 'gs://bucket/test.ipynb'), 2
                    )

    @patch(
        'papermill.iorw.GCSFileSystem',
        side_effect=mock_gcs_fs_wrapper(GCSHttpError({"message": "test", "code": 429}), 1),
    )
    def test_gcs_retry_older_exception(self, mock_gcs_filesystem):
        with patch.object(GCSHandler, 'RETRY_DELAY', 0):
            with patch.object(GCSHandler, 'RETRY_MULTIPLIER', 0):
                with patch.object(GCSHandler, 'RETRY_MAX_DELAY', 0):
                    self.assertEqual(
                        self.gcs_handler.write('raise_limit_exception', 'gs://bucket/test.ipynb'), 2
                    )

    @patch('papermill.iorw.gs_is_retriable', side_effect=fallback_gs_is_retriable)
    @patch(
        'papermill.iorw.GCSFileSystem',
        side_effect=mock_gcs_fs_wrapper(
            GCSRateLimitException({"message": "test", "code": None}), 1
        ),
    )
    def test_gcs_fallback_retry_unknown_failure_code(self, mock_gcs_filesystem, mock_gcs_retriable):
        with patch.object(GCSHandler, 'RETRY_DELAY', 0):
            with patch.object(GCSHandler, 'RETRY_MULTIPLIER', 0):
                with patch.object(GCSHandler, 'RETRY_MAX_DELAY', 0):
                    self.assertEqual(
                        self.gcs_handler.write('raise_limit_exception', 'gs://bucket/test.ipynb'), 2
                    )

    @patch('papermill.iorw.gs_is_retriable', return_value=False)
    @patch(
        'papermill.iorw.GCSFileSystem',
        side_effect=mock_gcs_fs_wrapper(GCSRateLimitException({"message": "test", "code": 500}), 1),
    )
    def test_gcs_invalid_code(self, mock_gcs_filesystem, mock_gcs_retriable):
        with self.assertRaises(GCSRateLimitException):
            self.gcs_handler.write('fatal_exception', 'gs://bucket/test.ipynb')

    @patch('papermill.iorw.gs_is_retriable', side_effect=fallback_gs_is_retriable)
    @patch(
        'papermill.iorw.GCSFileSystem',
        side_effect=mock_gcs_fs_wrapper(GCSRateLimitException({"message": "test", "code": 500}), 1),
    )
    def test_fallback_gcs_invalid_code(self, mock_gcs_filesystem, mock_gcs_retriable):
        with self.assertRaises(GCSRateLimitException):
            self.gcs_handler.write('fatal_exception', 'gs://bucket/test.ipynb')

    @patch(
        'papermill.iorw.GCSFileSystem',
        side_effect=mock_gcs_fs_wrapper(ValueError("not-a-retry"), 1),
    )
    def test_gcs_unretryable(self, mock_gcs_filesystem):
        with self.assertRaises(ValueError):
            self.gcs_handler.write('no_a_rate_limit', 'gs://bucket/test.ipynb')
