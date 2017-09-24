""" Test the command line interface """
import pytest

from ..cli import _is_float

def test_is_float():

    value = 18.7
    assert _is_float(value) == value

    value = 12
    assert _is_float(value) == value