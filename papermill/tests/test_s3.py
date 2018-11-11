# The following tests are purposely limited to the exposed interface by iorw.py

import os.path
import pytest
import boto3
import moto

from moto import mock_s3

from ..s3 import Bucket, Prefix, Key, S3


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
    with pytest.raises(TypeError):
        Prefix()

    with pytest.raises(TypeError):
        Prefix(service=None)

    with pytest.raises(TypeError):
        Prefix('my_test_prefix')

    b1 = Bucket('my_test_bucket')
    p1 = Prefix(b1, 'sqs_test', service='sqs')
    assert Prefix(b1, 'test_bucket')
    assert Prefix(b1, 'test_bucket', service=None)
    assert Prefix(b1, 'test_bucket', None)
    assert p1.bucket.service == p1.service


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
    assert repr(p1) == 's3://' + str(bucket_sqs) + '/sqs_prefix_test'


def test_key_init():
    pass


def test_key_repr():
    k = Key("foo", "bar")
    assert repr(k) == "s3://foo/bar"


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


@mock_s3
def test_s3_defaults():
    s1 = S3()
    s2 = S3()
    assert s1.session == s2.session
    assert s1.client == s2.client
    assert s1.s3 == s2.s3


local_dir = os.path.dirname(os.path.abspath(__file__))
test_bucket_name = 'test-pm-bucket'
test_string = 'Hello'
test_file_path = 'notebooks/s3/s3_in/s3-simple_notebook.ipynb'

with open(os.path.join(local_dir, test_file_path)) as f:
    test_nb_content = f.read()

no_empty_lines = lambda s: "\n".join([l for l in s.split('\n') if len(l) > 0])
test_clean_nb_content = no_empty_lines(test_nb_content)

read_from_gen = lambda g: "\n".join(g)


@pytest.yield_fixture(scope="function")
def s3_client():
    mock_s3 = moto.mock_s3()
    mock_s3.start()

    client = boto3.client('s3')
    client.create_bucket(Bucket=test_bucket_name)
    client.put_object(Bucket=test_bucket_name, Key=test_file_path, Body=test_nb_content)
    yield S3()
    try:
        client.delete_object(Bucket=test_bucket_name, Key=test_file_path)
        client.delete_object(Bucket=test_bucket_name, Key=test_file_path + '.txt')
    except Exception:
        pass
    mock_s3.stop()


def test_s3_read(s3_client):
    s3_path = "s3://{}/{}".format(test_bucket_name, test_file_path)
    data = read_from_gen(s3_client.read(s3_path))
    assert data == test_clean_nb_content


def test_s3_write(s3_client):
    s3_path = "s3://{}/{}.txt".format(test_bucket_name, test_file_path)
    s3_client.cp_string(test_string, s3_path)

    data = read_from_gen(s3_client.read(s3_path))
    assert data == test_string


def test_s3_overwrite(s3_client):
    s3_path = "s3://{}/{}".format(test_bucket_name, test_file_path)
    s3_client.cp_string(test_string, s3_path)

    data = read_from_gen(s3_client.read(s3_path))
    assert data == test_string


def test_s3_listdir(s3_client):
    dir_name = os.path.dirname(test_file_path)
    s3_dir = "s3://{}/{}".format(test_bucket_name, dir_name)
    s3_path = "s3://{}/{}".format(test_bucket_name, test_file_path)
    dir_listings = s3_client.listdir(s3_dir)
    assert len(dir_listings) == 1
    assert s3_path in dir_listings
