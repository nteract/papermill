import pytest
from collections import OrderedDict

from ..translators import PythonTranslator, RTranslator, ScalaTranslator


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("foo", '"foo"'),
        ('{"foo": "bar"}', '"{\\"foo\\": \\"bar\\"}"'),
        ({"foo": "bar"}, '{"foo": "bar"}'),
        ({"foo": '"bar"'}, '{"foo": "\\"bar\\""}'),
        ({"foo": ["bar"]}, '{"foo": ["bar"]}'),
        ({"foo": {"bar": "baz"}}, '{"foo": {"bar": "baz"}}'),
        ({"foo": {"bar": '"baz"'}}, '{"foo": {"bar": "\\"baz\\""}}'),
        (["foo"], '["foo"]'),
        (["foo", '"bar"'], '["foo", "\\"bar\\""]'),
        ([{"foo": "bar"}], '[{"foo": "bar"}]'),
        ([{"foo": '"bar"'}], '[{"foo": "\\"bar\\""}]'),
        (12345, '12345'),
        (-54321, '-54321'),
        (1.2345, '1.2345'),
        (-5432.1, '-5432.1'),
        (True, 'True'),
        (False, 'False'),
    ],
)
def test_translate_type_python(test_input, expected):
    assert PythonTranslator.translate(test_input) == expected


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"foo": "bar"}, '# Parameters\nfoo = "bar"\n'),
        ({"foo": True}, '# Parameters\nfoo = True\n'),
        ({"foo": 5}, '# Parameters\nfoo = 5\n'),
        ({"foo": 1.1}, '# Parameters\nfoo = 1.1\n'),
        ({"foo": ['bar', 'baz']}, '# Parameters\nfoo = ["bar", "baz"]\n'),
        ({"foo": {'bar': 'baz'}}, '# Parameters\nfoo = {"bar": "baz"}\n'),
        (
            OrderedDict([['foo', 'bar'], ['baz', ['buz']]]),
            '# Parameters\nfoo = "bar"\nbaz = ["buz"]\n',
        ),
    ],
)
def test_translate_codify_python(parameters, expected):
    assert PythonTranslator.codify(parameters) == expected


@pytest.mark.parametrize(
    "test_input,expected", [("", '#'), ("foo", '# foo'), ("['best effort']", "# ['best effort']")]
)
def test_translate_comment_python(test_input, expected):
    assert PythonTranslator.comment(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("foo", '"foo"'),
        ('{"foo": "bar"}', '"{\\"foo\\": \\"bar\\"}"'),
        ({"foo": "bar"}, 'list("foo" = "bar")'),
        ({"foo": '"bar"'}, 'list("foo" = "\\"bar\\"")'),
        ({"foo": ["bar"]}, 'list("foo" = list("bar"))'),
        ({"foo": {"bar": "baz"}}, 'list("foo" = list("bar" = "baz"))'),
        ({"foo": {"bar": '"baz"'}}, 'list("foo" = list("bar" = "\\"baz\\""))'),
        (["foo"], 'list("foo")'),
        (["foo", '"bar"'], 'list("foo", "\\"bar\\"")'),
        ([{"foo": "bar"}], 'list(list("foo" = "bar"))'),
        ([{"foo": '"bar"'}], 'list(list("foo" = "\\"bar\\""))'),
        (12345, '12345'),
        (-54321, '-54321'),
        (1.2345, '1.2345'),
        (-5432.1, '-5432.1'),
        (True, 'TRUE'),
        (False, 'FALSE'),
    ],
)
def test_translate_type_r(test_input, expected):
    assert RTranslator.translate(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected", [("", '#'), ("foo", '# foo'), ("['best effort']", "# ['best effort']")]
)
def test_translate_comment_r(test_input, expected):
    assert RTranslator.comment(test_input) == expected


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"foo": "bar"}, '# Parameters\nfoo = "bar"\n'),
        ({"foo": True}, '# Parameters\nfoo = TRUE\n'),
        ({"foo": 5}, '# Parameters\nfoo = 5\n'),
        ({"foo": 1.1}, '# Parameters\nfoo = 1.1\n'),
        ({"foo": ['bar', 'baz']}, '# Parameters\nfoo = list("bar", "baz")\n'),
        ({"foo": {'bar': 'baz'}}, '# Parameters\nfoo = list("bar" = "baz")\n'),
        (
            OrderedDict([['foo', 'bar'], ['baz', ['buz']]]),
            '# Parameters\nfoo = "bar"\nbaz = list("buz")\n',
        ),
    ],
)
def test_translate_codify_r(parameters, expected):
    assert RTranslator.codify(parameters) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("foo", '"foo"'),
        ('{"foo": "bar"}', '"{\\"foo\\": \\"bar\\"}"'),
        ({"foo": "bar"}, 'Map("foo" -> "bar")'),
        ({"foo": '"bar"'}, 'Map("foo" -> "\\"bar\\"")'),
        ({"foo": ["bar"]}, 'Map("foo" -> Seq("bar"))'),
        ({"foo": {"bar": "baz"}}, 'Map("foo" -> Map("bar" -> "baz"))'),
        ({"foo": {"bar": '"baz"'}}, 'Map("foo" -> Map("bar" -> "\\"baz\\""))'),
        (["foo"], 'Seq("foo")'),
        (["foo", '"bar"'], 'Seq("foo", "\\"bar\\"")'),
        ([{"foo": "bar"}], 'Seq(Map("foo" -> "bar"))'),
        ([{"foo": '"bar"'}], 'Seq(Map("foo" -> "\\"bar\\""))'),
        (12345, '12345'),
        (-54321, '-54321'),
        (1.2345, '1.2345'),
        (-5432.1, '-5432.1'),
        (2147483648, '2147483648L'),
        (-2147483649, '-2147483649L'),
        (True, 'true'),
        (False, 'false'),
    ],
)
def test_translate_type_scala(test_input, expected):
    assert ScalaTranslator.translate(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [("", '//'), ("foo", '// foo'), ("['best effort']", "// ['best effort']")],
)
def test_translate_comment_scala(test_input, expected):
    assert ScalaTranslator.comment(test_input) == expected


@pytest.mark.parametrize(
    "input_name,input_value,expected",
    [
        ("foo", '""', 'val foo = ""'),
        ("foo", '"bar"', 'val foo = "bar"'),
        ("foo", 'Map("foo" -> "bar")', 'val foo = Map("foo" -> "bar")'),
    ],
)
def test_translate_assign_scala(input_name, input_value, expected):
    assert ScalaTranslator.assign(input_name, input_value) == expected


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"foo": "bar"}, '// Parameters\nval foo = "bar"\n'),
        ({"foo": True}, '// Parameters\nval foo = true\n'),
        ({"foo": 5}, '// Parameters\nval foo = 5\n'),
        ({"foo": 1.1}, '// Parameters\nval foo = 1.1\n'),
        ({"foo": ['bar', 'baz']}, '// Parameters\nval foo = Seq("bar", "baz")\n'),
        ({"foo": {'bar': 'baz'}}, '// Parameters\nval foo = Map("bar" -> "baz")\n'),
        (
            OrderedDict([['foo', 'bar'], ['baz', ['buz']]]),
            '// Parameters\nval foo = "bar"\nval baz = Seq("buz")\n',
        ),
    ],
)
def test_translate_codify_scala(parameters, expected):
    assert ScalaTranslator.codify(parameters) == expected
