#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Test the command line interface """

import pytest

from ..cli import _is_int,  _is_float, _resolve_type


@pytest.mark.parametrize("test_input,expected", [
    ("True", True),
    ("False", False),
    ("None", None),
    (13.3, 13.3),
    ("12.51", 12.51),
    (10, 10),
    ("10", 10),
    ("hello world", "hello world"),
    (u"😍", u"😍"),
])
def test_resolve_type(test_input, expected):
    assert _resolve_type(test_input) == expected


@pytest.mark.parametrize("value,expected", [
    (13.71, True),
    ("False", False),
    ("None", False),
    (-8.2, True),
    (10, False),
    ("hello world", False),
    ("😍", False),
])
def test_is_float(value, expected):
    assert (_is_float(value)) == expected


@pytest.mark.parametrize("value,expected", [
    (13.71, False),
    ("False", False),
    ("None", False),
    (-8.2, False),
    ("-23.2", False),
    (10, True),
    ("13", True),
    ("hello world", False),
    ("😍", False),
])
def test_is_int(value, expected):
    assert (_is_int(value)) == expected
