import pytest

from ..s3 import Bucket, split


def test_bucket_init():
    name = 'hello world'
    test_bucket = Bucket(name, service=None)
    assert test_bucket.name is name


def test_bucket_missing_params():
    with pytest.raises(TypeError):
        Bucket(service=None)

    with pytest.raises(TypeError):
        Bucket()


def test_bucket_list():
    pass


@pytest.mark.parametrize("value,expected", [
    ('s3://foo/bar/baz', ['foo', 'bar/baz']),
    ('s3://foo/bar/baz/', ['foo', 'bar/baz/'])
])
def test_split_success(value, expected):
    assert (split(value)) == expected


def test_split_error():

    with pytest.raises(ValueError):
        split('foo/bar/baz')

    with pytest.raises(ValueError):
        split('https://foo/bar/baz')

