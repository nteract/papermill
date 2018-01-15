import pytest

from ..s3 import Bucket, Prefix, Key, S3, split


@pytest.fixture
def bucket_no_service():
    """Returns a bucket instance with no services"""
    return Bucket('my_test_bucket')


@pytest.fixture
def bucket_with_service():
    """Returns a bucket instance with a service"""
    return Bucket('my_sqs_bucket', ['sqs'])


@pytest.fixture
def bucket_sqs():
    """Returns a bucket instance with a sqs service"""
    return Bucket('my_sqs_bucket', ['sqs'])

@pytest.fixture
def bucket_ec2():
    """Returns a bucket instance with a ec2 service"""
    return Bucket('my_sqs_bucket', ['ec2'])

@pytest.fixture
def bucket_multiservice():
    """Returns a bucket instance with a ec2 service"""
    return Bucket('my_sqs_bucket', ['ec2', 'sqs'])

def test_bucket_init():
    assert Bucket('my_test_bucket')
    assert Bucket('my_sqs_bucket', 'sqs')


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


def test_bucket_list(bucket_sqs):
    # prefix_test = ''
    # assert bucket_sqs.list(prefix_test)
    #
    # prefix_test = 'abc'
    # assert bucket_sqs.list(prefix_test) is None
    #
    # prefix_test = 'ec2'
    # assert bucket_sqs.list(prefix_test) is None
    #
    # prefix_test = 'sqs'
    # assert bucket_sqs.list(prefix_test)
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


def test_prefix_str(bucket_sqs):
    p1 = Prefix(bucket_sqs, 'sqs_prefix_test', 'sqs')
    assert str(p1) == 's3://' + str(bucket_sqs) + '/sqs_prefix_test'


def test_prefix_repr(bucket_sqs):
    p1 = Prefix(bucket_sqs, 'sqs_prefix_test', 'sqs')
    assert p1.__repr__


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

