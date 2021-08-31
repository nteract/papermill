import pickle
import tempfile

import pytest  # noqa

from .. import exceptions


@pytest.fixture
def temp_file():
    f = tempfile.NamedTemporaryFile()
    yield f
    f.close()


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
    with open(temp_file.name, 'wb') as fd:
        pickle.dump(err, fd)
    # Read the Pickled File
    temp_file.seek(0)
    data = temp_file.read()
    pickled_err = pickle.loads(data)
    assert str(pickled_err) == str(err)
