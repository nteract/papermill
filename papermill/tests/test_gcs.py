from ..iorw import GCSHandler


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

    def write(self, data):
        pass


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


def test_gcs_listdir(mocker):
    mocker.patch('papermill.iorw.GCSFileSystem', MockGCSFileSystem)
    gcs_handler = GCSHandler()
    client = gcs_handler._get_client()
    gcs_handler.listdir('testdir')

    # Check that client is only generated once
    assert client is gcs_handler._get_client()
