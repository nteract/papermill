import json
import unittest
import six
if six.PY3:
    from unittest.mock import Mock, patch
else:
    from mock import Mock, patch

from ..exceptions import PapermillException
from ..iorw import HttpHandler


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

        self.assertEqual(
                '{}'.format(e.exception), 'listdir is not supported by HttpHandler'
        )

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
            mock_get.assert_called_once_with(path)

    def test_write(self):
        """
        Tests that the `write` function performs a request a put request to
        the giving path.
        """
        path = 'http://example.com'
        buf = '{"papermill": true}'

        with patch('papermill.iorw.requests.put') as mock_put:
            HttpHandler.write(buf, path)
            mock_put.assert_called_once_with(path, json=json.loads(buf))
