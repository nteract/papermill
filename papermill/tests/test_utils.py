import os
import six
import pytest

try:
    from tempfile import TemporaryDirectory
except ImportError:
    # python 2
    from backports.tempfile import TemporaryDirectory
from ..utils import retry, chdir

if six.PY3:
    from unittest.mock import Mock, call
else:
    from mock import Mock, call


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
