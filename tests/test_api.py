import unittest

import pandas as pd
from pandas.util.testing import assert_frame_equal
from papermill import read_notebook
from tests import get_notebook_path


class TestNotebookClass(unittest.TestCase):

    def test(self):

        path = get_notebook_path('result_notebook.ipynb')
        nb = read_notebook(path)
        self.assertEqual(nb.parameters, dict(foo=1, bar="Hello World!"))
        expected_df = pd.DataFrame(
            [
                ('bar', 'Hello World!', 'parameter', 'result_notebook.ipynb'),
                ('foo', 1, 'parameter', 'result_notebook.ipynb'),
                ('dict', {u'a': 1, u'b': 2}, 'record', 'result_notebook.ipynb'),
                ('list', [1, 2, 3], 'record', 'result_notebook.ipynb'),
                ('number', 1, 'record', 'result_notebook.ipynb'),
            ],
            columns=['name', 'value', 'type', 'filename']
        )
        assert_frame_equal(nb.dataframe, expected_df)
