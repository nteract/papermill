import pytest

from ..s3 import Bucket, split


def test_bucket_init():
    name = 'hello world'
    test_bucket = Bucket(name, service=None)
    assert test_bucket.name is name


def test_bucket_missing_params():
    with pytest.raises(TypeError):
        Bucket('', service=None)

    with pytest.raises(TypeError):
        Bucket('')


def test_bucket_list():
    pass


@pytest.mark.parametrize("path,expected", [
    ('s3://foo/bar/baz', ['foo', 'bar/baz']),
    ('foo/bar/baz', ValueError),
    ('s3://foo/bar/baz/', ['foo', 'bar/baz/']),
    ('https://foo/bar/baz', ValueError),
])
def test_split(path, expected):
    assert split(path) == expected
