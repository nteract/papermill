import os
import pickle
import tempfile

import pytest

from .. import exceptions


@pytest.fixture
def temp_file():
    """NamedTemporaryFile must be set in wb mode, closed without delete, opened with open(file, "rb"),
    then manually deleted. Otherwise, file fails to be read due to permission error on Windows."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        yield f
        os.unlink(f.name)


@pytest.mark.parametrize(
    "exc,args",
    [
        (
            exceptions.PapermillExecutionError,
            (1, 2, "TestSource", "Exception", Exception(), ["Traceback", "Message"]),
        ),
        (exceptions.PapermillMissingParameterException, ("PapermillMissingParameterException",)),
        (exceptions.AwsError, ("AwsError",)),
        (exceptions.FileExistsError, ("FileExistsError",)),
        (exceptions.PapermillException, ("PapermillException",)),
        (exceptions.PapermillRateLimitException, ("PapermillRateLimitException",)),
        (
            exceptions.PapermillOptionalDependencyException,
            ("PapermillOptionalDependencyException",),
        ),
    ],
)
def test_exceptions_are_unpickleable(temp_file, exc, args):
    """Ensure exceptions can be unpickled"""
    err = exc(*args)
    pickle.dump(err, temp_file)
    temp_file.close()  # close to re-open for reading

    # Read the Pickled File
    with open(temp_file.name, "rb") as read_file:
        read_file.seek(0)
        data = read_file.read()
        pickled_err = pickle.loads(data)
        assert str(pickled_err) == str(err)
