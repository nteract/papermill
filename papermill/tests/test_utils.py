import os
import pytest
import warnings

from unittest.mock import Mock, call
from tempfile import TemporaryDirectory

from nbformat.v4 import new_notebook, new_code_cell

from ..utils import (
    any_tagged_cell,
    retry,
    chdir,
    merge_kwargs,
    remove_args,
)
from ..exceptions import PapermillParameterOverwriteWarning


def test_no_tagged_cell():
    nb = new_notebook(cells=[new_code_cell('a = 2', metadata={"tags": []})],)
    assert not any_tagged_cell(nb, "parameters")


def test_tagged_cell():
    nb = new_notebook(cells=[new_code_cell('a = 2', metadata={"tags": ["parameters"]})],)
    assert any_tagged_cell(nb, "parameters")


def test_merge_kwargs():
    with warnings.catch_warnings(record=True) as wrn:
        assert merge_kwargs({"a": 1, "b": 2}, a=3) == {"a": 3, "b": 2}
        assert len(wrn) == 1
        assert issubclass(wrn[0].category, PapermillParameterOverwriteWarning)
        assert wrn[0].message.__str__() == "Callee will overwrite caller's argument(s): a=3"


def test_remove_args():
    assert remove_args(["a"], a=1, b=2, c=3) == {"c": 3, "b": 2}


def test_retry():
    m = Mock(side_effect=RuntimeError(), __name__="m", __module__="test_s3", __doc__="m")
    wrapped_m = retry(3)(m)
    with pytest.raises(RuntimeError):
        wrapped_m("foo")
    m.assert_has_calls([call("foo"), call("foo"), call("foo")])


def test_chdir():
    old_cwd = os.getcwd()
    with TemporaryDirectory() as temp_dir:
        with chdir(temp_dir):
            assert os.getcwd() != old_cwd
            assert os.getcwd() == os.path.realpath(temp_dir)

    assert os.getcwd() == old_cwd
