import os
import pickle
import tempfile

import pytest  # noqa

from .. import exceptions


@pytest.fixture
def temp_file():
    f = tempfile.NamedTemporaryFile()
    yield f
    f.close()


def test_exceptions_are_unpickleable(temp_file):
    """Ensure Exceptions can be unpickled"""
    err = exceptions.PapermillExecutionError(1, 2, "TestSource", "Exception", Exception(), ["Traceback", "Message"])
    with open(temp_file.name, 'wb') as fd:
        pickle.dump(err, fd)
    # Read File
    temp_file.seek(0)
    data = temp_file.read()
    pickled_err = pickle.loads(data)
    assert str(pickled_err) == str(err)
