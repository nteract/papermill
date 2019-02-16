from ..iorw import GCSHandler


class RetryableError(Exception):
    pass


class MockGCSFileSystem(object):
    def __init__(self):
        self._file = MockGCSFile()

    def open(self, *args, **kwargs):
        return self._file

    def ls(self, *args, **kwargs):
        return []


class MockGCSFile(object):
    def __enter__(self):
        self._value = 'default value'
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def read(self):
        return self._value

    def write(self, buf):
        if not buf:
            raise RetryableError


def test_gcs_read(mocker):
    mocker.patch('papermill.iorw.GCSFileSystem', MockGCSFileSystem)
    gcs_handler = GCSHandler()
    client = gcs_handler._get_client()
    assert gcs_handler.read('gs://bucket/test.ipynb') == 'default value'

    # Check that client is only generated once
    assert client is gcs_handler._get_client()


def test_gcs_write(mocker):
    mocker.patch('papermill.iorw.GCSFileSystem', MockGCSFileSystem)
    gcs_handler = GCSHandler()
    client = gcs_handler._get_client()
    gcs_handler.write('new value', 'gs://bucket/test.ipynb')
    # Check that client is only generated once
    assert client is gcs_handler._get_client()


def test_gcs_write_retry(mocker):
    mocker.patch('papermill.iorw.GCSFileSystem', MockGCSFileSystem)
    counter = 0
    try:
        gcs_handler = GCSHandler()
        client = gcs_handler._get_client()
        gcs_handler.write('', 'gs://bucket/test.ipynb')
    except RetryableError:
        counter += 1
    assert counter == 1
    # Check that client is only generated once
    assert client is gcs_handler._get_client()


def test_gcs_listdir(mocker):
    mocker.patch('papermill.iorw.GCSFileSystem', MockGCSFileSystem)
    gcs_handler = GCSHandler()
    client = gcs_handler._get_client()
    gcs_handler.listdir('testdir')

    # Check that client is only generated once
    assert client is gcs_handler._get_client()
