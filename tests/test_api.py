import unittest

import pandas as pd
import papermill as pm
from pandas.util.testing import assert_frame_equal
from tests import get_notebook_path


class TestGetData(unittest.TestCase):

    def test_get_data(self):

        nb_path = get_notebook_path('directory', 'input_1.ipynb')
        data = pm.fetch_notebook_data(nb_path)
        self.assertEqual(data, {'hello': 1, 'world': 2})

    def test_get_dataframe(self):

        nb_dir = get_notebook_path('directory')
        df = pm.fetch_notebooks_dataframe(nb_dir)

        expected_df = pd.DataFrame(
            [{'hello': 1, 'world': 2}, {'hello': 10, 'world': 20}],
            index=['input_1.ipynb', 'input_2.ipynb']
        )
        assert_frame_equal(df, expected_df)
