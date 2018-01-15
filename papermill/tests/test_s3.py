import pytest

from ..s3 import Bucket, Prefix, Key, S3, split


def test_bucket_init():
    name = 'hello world'
    test_bucket = Bucket(name, service=None)
    assert test_bucket.name is name


def test_bucket_defaults():
    name = 'a bucket'

    b1 = Bucket(name)
    b2 = Bucket(name, None)

    assert b1.name == b2.name
    assert b1.service == b2.service


def test_bucket_missing_params():
    with pytest.raises(TypeError):
        Bucket(service=None)

    with pytest.raises(TypeError):
        Bucket()


def test_bucket_list():
    pass


def test_prefix_init():
    pass


def test_prefix_defaults():
    bucket = Bucket('my data pool')
    name = 'bigdata bucket'

    p1 = Prefix(bucket, name)
    p2 = Prefix(bucket, name, None)
    assert p1.name == p2.name
    assert p1.service == p2.service
    assert p1.is_prefix is True


def test_key_init():
    pass


def test_key_defaults():
    bucket = Bucket('my data pool')
    name = 'bigdata bucket'

    k1 = Key(bucket, name)
    k2 = Key(bucket, name, None, None, None, None, None)
    assert k1.size == k2.size
    assert k1.etag == k2.etag
    assert k1.storage_class == k2.storage_class
    assert k1.service == k2.service
    assert k1.is_prefix is False


def test_s3_defaults():
    s1 = S3()
    s2 = S3(None, None, None, 'us-east-1')
    assert s1.session == s2.session
    assert s1.client == s2.client
    assert s1.s3 == s2.s3

@pytest.mark.parametrize("value,expected", [
    ('s3://foo/bar/baz', ['foo', 'bar/baz']),
    ('s3://foo/bar/baz/', ['foo', 'bar/baz/']),
    ('s3://foo', ['foo', '']),
    ('s3://', ['', '']),
    ('s3:///', ['', '']),
])
def test_split_success(value, expected):
    assert (split(value)) == expected


def test_split_error():

    with pytest.raises(ValueError):
        split('foo/bar/baz')

    with pytest.raises(ValueError):
        split('https://foo/bar/baz')

