import pytest
from collections import OrderedDict
from .. import translators
from ..exceptions import PapermillException

import six

if six.PY3:
    from unittest.mock import Mock
else:
    from mock import Mock


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
        (None, 'None'),
    ],
)
def test_translate_type_python(test_input, expected):
    assert translators.PythonTranslator.translate(test_input) == expected


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
    assert translators.PythonTranslator.codify(parameters) == expected


@pytest.mark.parametrize(
    "test_input,expected", [("", '#'), ("foo", '# foo'), ("['best effort']", "# ['best effort']")]
)
def test_translate_comment_python(test_input, expected):
    assert translators.PythonTranslator.comment(test_input) == expected


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
        (None, 'NULL'),
    ],
)
def test_translate_type_r(test_input, expected):
    assert translators.RTranslator.translate(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected", [("", '#'), ("foo", '# foo'), ("['best effort']", "# ['best effort']")]
)
def test_translate_comment_r(test_input, expected):
    assert translators.RTranslator.comment(test_input) == expected


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
    assert translators.RTranslator.codify(parameters) == expected


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
        (None, 'None'),
    ],
)
def test_translate_type_scala(test_input, expected):
    assert translators.ScalaTranslator.translate(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [("", '//'), ("foo", '// foo'), ("['best effort']", "// ['best effort']")],
)
def test_translate_comment_scala(test_input, expected):
    assert translators.ScalaTranslator.comment(test_input) == expected


@pytest.mark.parametrize(
    "input_name,input_value,expected",
    [
        ("foo", '""', 'val foo = ""'),
        ("foo", '"bar"', 'val foo = "bar"'),
        ("foo", 'Map("foo" -> "bar")', 'val foo = Map("foo" -> "bar")'),
    ],
)
def test_translate_assign_scala(input_name, input_value, expected):
    assert translators.ScalaTranslator.assign(input_name, input_value) == expected


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
    assert translators.ScalaTranslator.codify(parameters) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("foo", '"foo"'),
        ('{"foo": "bar"}', '"{\\"foo\\": \\"bar\\"}"'),
        ({"foo": "bar"}, 'Dict("foo" => "bar")'),
        ({"foo": '"bar"'}, 'Dict("foo" => "\\"bar\\"")'),
        ({"foo": ["bar"]}, 'Dict("foo" => ["bar"])'),
        ({"foo": {"bar": "baz"}}, 'Dict("foo" => Dict("bar" => "baz"))'),
        ({"foo": {"bar": '"baz"'}}, 'Dict("foo" => Dict("bar" => "\\"baz\\""))'),
        (["foo"], '["foo"]'),
        (["foo", '"bar"'], '["foo", "\\"bar\\""]'),
        ([{"foo": "bar"}], '[Dict("foo" => "bar")]'),
        ([{"foo": '"bar"'}], '[Dict("foo" => "\\"bar\\"")]'),
        (12345, '12345'),
        (-54321, '-54321'),
        (1.2345, '1.2345'),
        (-5432.1, '-5432.1'),
        (True, 'true'),
        (False, 'false'),
        (None, 'nothing'),
    ],
)
def test_translate_type_julia(test_input, expected):
    assert translators.JuliaTranslator.translate(test_input) == expected


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"foo": "bar"}, '# Parameters\nfoo = "bar"\n'),
        ({"foo": True}, '# Parameters\nfoo = true\n'),
        ({"foo": 5}, '# Parameters\nfoo = 5\n'),
        ({"foo": 1.1}, '# Parameters\nfoo = 1.1\n'),
        ({"foo": ['bar', 'baz']}, '# Parameters\nfoo = ["bar", "baz"]\n'),
        ({"foo": {'bar': 'baz'}}, '# Parameters\nfoo = Dict("bar" => "baz")\n'),
        (
            OrderedDict([['foo', 'bar'], ['baz', ['buz']]]),
            '# Parameters\nfoo = "bar"\nbaz = ["buz"]\n',
        ),
    ],
)
def test_translate_codify_julia(parameters, expected):
    assert translators.JuliaTranslator.codify(parameters) == expected


@pytest.mark.parametrize(
    "test_input,expected", [("", '#'), ("foo", '# foo'), ('["best effort"]', '# ["best effort"]')]
)
def test_translate_comment_julia(test_input, expected):
    assert translators.JuliaTranslator.comment(test_input) == expected


def test_find_translator_with_exact_kernel_name():
    my_new_kernel_translator = Mock()
    my_new_language_translator = Mock()
    translators.papermill_translators.register("my_new_kernel", my_new_kernel_translator)
    translators.papermill_translators.register("my_new_language", my_new_language_translator)
    assert (
        translators.papermill_translators.find_translator("my_new_kernel", "my_new_language")
        is my_new_kernel_translator
    )


def test_find_translator_with_exact_language():
    my_new_language_translator = Mock()
    translators.papermill_translators.register("my_new_language", my_new_language_translator)
    assert (
        translators.papermill_translators.find_translator("unregistered_kernel", "my_new_language")
        is my_new_language_translator
    )


def test_find_translator_with_no_such_kernel_or_language():
    with pytest.raises(PapermillException):
        translators.papermill_translators.find_translator(
            "unregistered_kernel", "unregistered_language"
        )


def test_translate_uses_str_representation_of_unknown_types():
    class FooClass:
        def __str__(self):
            return "foo"

    obj = FooClass()
    assert translators.Translator.translate(obj) == '"foo"'


def test_translator_must_implement_translate_dict():
    class MyNewTranslator(translators.Translator):
        pass

    with pytest.raises(NotImplementedError):
        MyNewTranslator.translate_dict({"foo": "bar"})


def test_translator_must_implement_translate_list():
    class MyNewTranslator(translators.Translator):
        pass

    with pytest.raises(NotImplementedError):
        MyNewTranslator.translate_list(["foo", "bar"])


def test_translator_must_implement_comment():
    class MyNewTranslator(translators.Translator):
        pass

    with pytest.raises(NotImplementedError):
        MyNewTranslator.comment("foo")
