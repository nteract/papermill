import unittest
import six

from ..abs import AzureBlobStore

if six.PY3:
    from unittest.mock import Mock
else:
    from mock import Mock


class ABSTest(unittest.TestCase):
    """
    Tests for `ABS`
    """

    def setUp(self):
        self.list_blobs = Mock(return_value=["foo", "bar", "baz"])
        self.get_blob_to_text = Mock(return_value=["hello"])
        self.create_blob_from_text = Mock()
        self._block_blob_service = Mock(
            get_blob_to_text=self.get_blob_to_text,
            list_blobs=self.list_blobs,
            create_blob_from_text=self.create_blob_from_text,
        )
        self.abs = AzureBlobStore()
        self.abs._block_blob_service = Mock(return_value=self._block_blob_service)

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
        self.list_blobs.assert_called_once_with("sascontainer")

    def test_reads_file(self):
        self.assertEquals(
            self.abs.read(
                "abs://myaccount.blob.core.windows.net/sascontainer/sasblob.txt?sastoken"
            ),
            ["hello"],
        )
        self.get_blob_to_text.assert_called_once_with(
            container_name="sascontainer", blob_name="sasblob.txt"
        )

    def test_write_file(self):
        self.abs.write(
            "hello world", "abs://myaccount.blob.core.windows.net/sascontainer/sasblob.txt?sastoken"
        )
        self.create_blob_from_text.assert_called_once_with(
            container_name="sascontainer", blob_name="sasblob.txt", text="hello world"
        )

    def test__block_blob_service(self):
        abs = AzureBlobStore()
        blob = abs._block_blob_service(account_name="myaccount", sas_token="sastoken")
        self.assertEqual(blob.account_name, "myaccount")
        self.assertEqual(blob.sas_token, "sastoken")
        self.assertEqual(blob.blob_type, "BlockBlob")
