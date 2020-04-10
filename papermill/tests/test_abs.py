import unittest

from unittest.mock import Mock, patch

from ..abs import AzureBlobStore


class MockBytesIO(object):
    def __init__(self):
        self.list = [b"hello", b"world!"]

    def __getitem__(self, index):
        return self.list[index]

    def seek(self, seed):
        pass


class ABSTest(unittest.TestCase):
    """
    Tests for `ABS`
    """

    def setUp(self):
        self.list_blobs = Mock(return_value=["foo", "bar", "baz"])
        self.upload_blob = Mock()
        self.download_blob = Mock()
        self._container_client = Mock(list_blobs=self.list_blobs)
        self._blob_client = Mock(upload_blob=self.upload_blob, download_blob=self.download_blob)
        self._blob_service_client = Mock(
            get_blob_client=Mock(return_value=self._blob_client),
            get_container_client=Mock(return_value=self._container_client),
        )
        self.abs = AzureBlobStore()
        self.abs._blob_service_client = Mock(return_value=self._blob_service_client)

    def test_split_url_raises_exception_on_invalid_url(self):
        with self.assertRaises(Exception) as context:
            AzureBlobStore._split_url("this_is_not_a_valid_url")
        self.assertTrue(
            "Invalid azure blob url 'this_is_not_a_valid_url'" in str(context.exception)
        )

    def test_split_url_splits_valid_url(self):
        params = AzureBlobStore._split_url(
            "abs://myaccount.blob.core.windows.net/sascontainer/sasblob.txt?sastoken"
        )
        self.assertEqual(params["account"], "myaccount")
        self.assertEqual(params["container"], "sascontainer")
        self.assertEqual(params["blob"], "sasblob.txt")
        self.assertEqual(params["sas_token"], "sastoken")

    def test_listdir_calls(self):
        self.assertEqual(
            self.abs.listdir(
                "abs://myaccount.blob.core.windows.net/sascontainer/sasblob.txt?sastoken"
            ),
            ["foo", "bar", "baz"],
        )
        self._blob_service_client.get_container_client.assert_called_once_with("sascontainer")
        self.list_blobs.assert_called_once_with("sasblob.txt")

    @patch("papermill.abs.io.BytesIO", side_effect=MockBytesIO)
    def test_reads_file(self, mockBytesIO):
        self.assertEqual(
            self.abs.read(
                "abs://myaccount.blob.core.windows.net/sascontainer/sasblob.txt?sastoken"
            ),
            ["hello", "world!"],
        )
        self._blob_service_client.get_blob_client.assert_called_once_with(
            "sascontainer", "sasblob.txt"
        )
        self.download_blob.assert_called_once_with()

    def test_write_file(self):
        self.abs.write(
            "hello world", "abs://myaccount.blob.core.windows.net/sascontainer/sasblob.txt?sastoken"
        )
        self._blob_service_client.get_blob_client.assert_called_once_with(
            "sascontainer", "sasblob.txt"
        )
        self.upload_blob.assert_called_once_with(data="hello world", overwrite=True)

    def test_blob_service_client(self):
        abs = AzureBlobStore()
        blob = abs._blob_service_client(account_name="myaccount", sas_token="sastoken")
        self.assertEqual(blob.account_name, "myaccount")
        # Credentials gets funky with v12.0.0, so I comment this out
        # self.assertEqual(blob.credential, "sastoken")
