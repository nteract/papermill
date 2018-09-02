import unittest
from ..adl import ADL, core as adl_core, lib as adl_lib

import six

if six.PY3:
    from unittest.mock import Mock, MagicMock, patch
else:
    from mock import Mock, MagicMock, patch


class ADLTest(unittest.TestCase):
    """
    Tests for `ADL`
    """

    def setUp(self):
        self.ls = Mock(return_value=["foo", "bar", "baz"])
        self.fakeFile = MagicMock()
        self.fakeFile.__iter__.return_value = [b"a", b"b", b"c"]
        self.fakeFile.__enter__.return_value = self.fakeFile
        self.open = Mock(return_value=self.fakeFile)
        self.fakeAdapter = Mock(open=self.open, ls=self.ls)
        self.adl = ADL()
        self.adl._create_adapter = Mock(return_value=self.fakeAdapter)

    def test_split_url_raises_exception_on_invalid_url(self):
        with self.assertRaises(Exception) as context:
            ADL._split_url("this_is_not_a_valid_url")
        self.assertTrue("Invalid ADL url 'this_is_not_a_valid_url'" in str(context.exception))

    def test_split_url_splits_valid_url(self):
        (store_name, path) = ADL._split_url("adl://foo.azuredatalakestore.net/bar/baz")
        self.assertEqual(store_name, "foo")
        self.assertEqual(path, "bar/baz")

    def test_listdir_calls_ls_on_adl_adapter(self):
        self.assertEqual(
            self.adl.listdir("adl://foo_store.azuredatalakestore.net/path/to/file"),
            ["foo", "bar", "baz"],
        )
        self.ls.assert_called_once_with("path/to/file")

    def test_read_opens_and_reads_file(self):
        self.assertEquals(
            self.adl.read("adl://foo_store.azuredatalakestore.net/path/to/file"), ["a", "b", "c"]
        )
        self.fakeFile.__iter__.assert_called_once_with()

    def test_write_opens_file_and_writes_to_it(self):
        self.adl.write("hello world", "adl://foo_store.azuredatalakestore.net/path/to/file")
        self.fakeFile.write.assert_called_once_with(b"hello world")

    @patch.object(adl_lib, 'auth', return_value="my_token")
    @patch.object(adl_core, 'AzureDLFileSystem', return_value="my_adapter")
    def test_create_adapter(self, azure_dl_filesystem_mock, auth_mock):
        sut = ADL()
        actual = sut._create_adapter("my_store_name")
        assert actual == "my_adapter"
        auth_mock.assert_called_once_with()
        azure_dl_filesystem_mock.assert_called_once_with("my_token", store_name="my_store_name")
