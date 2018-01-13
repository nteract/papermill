import pytest

from ..s3 import Bucket


def test_bucket_init():
    name = 'hello world'
    test_bucket = Bucket(name, service=None)
    assert test_bucket.name is name


def test_bucket_missing_params():
    with pytest.raises(TypeError):
        test_bucket = Bucket(service=None)

    with pytest.raises(TypeError):
        test_bucket = Bucket()


def test_bucket_list():

    pass