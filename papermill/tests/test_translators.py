import pytest

from unittest.mock import Mock
from collections import OrderedDict

from nbformat.v4 import new_code_cell

from .. import translators
from ..exceptions import PapermillException
from ..models import Parameter


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
        (float('nan'), "float('nan')"),
        (float('-inf'), "float('-inf')"),
        (float('inf'), "float('inf')"),
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
        ("a = 2", [Parameter("a", "None", "2", "")]),
        ("a: int = 2", [Parameter("a", "int", "2", "")]),
        ("a = 2 # type:int", [Parameter("a", "int", "2", "")]),
        ("a = False # Nice variable a", [Parameter("a", "None", "False", "Nice variable a")]),
        ("a: float = 2.258 # type: int Nice variable a", [Parameter("a", "float", "2.258", "Nice variable a")]),  # noqa
        (
            "a = 'this is a string' # type: int Nice variable a",
            [Parameter("a", "int", "'this is a string'", "Nice variable a")]
        ),
        (
            "a: List[str] = ['this', 'is', 'a', 'string', 'list'] # Nice variable a",
            [Parameter("a", "List[str]", "['this', 'is', 'a', 'string', 'list']", "Nice variable a")]
        ),
        (
            "a: List[str] = [\n    'this', # First\n    'is',\n    'a',\n    'string',\n    'list' # Last\n] # Nice variable a",  # noqa
            [Parameter("a", "List[str]", "['this','is','a','string','list']", "Nice variable a")]
        ),
        (
            "a: List[str] = [\n    'this',\n    'is',\n    'a',\n    'string',\n    'list'\n] # Nice variable a",  # noqa
            [Parameter("a", "List[str]", "['this','is','a','string','list']", "Nice variable a")]
        ),
        (
            """a: List[str] = [
                'this', # First
                'is',

                'a',
                'string',
                'list' # Last
            ] # Nice variable a

            b: float = -2.3432 # My b variable
            """,
            [
                Parameter("a", "List[str]", "['this','is','a','string','list']", "Nice variable a"),
                Parameter("b", "float", "-2.3432", "My b variable"),
            ]
        ),
    ]
)
def test_inspect_python(test_input, expected):
    cell = new_code_cell(source=test_input)
    assert translators.PythonTranslator.inspect(cell) == expected


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
        # Underscores remove
        ({"___foo": 5}, '# Parameters\nfoo = 5\n'),
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


# C# section
@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("foo", '"foo"'),
        ('{"foo": "bar"}', '"{\\"foo\\": \\"bar\\"}"'),
        ({"foo": "bar"}, 'new Dictionary<string,Object>{ { "foo" , "bar" } }'),
        ({"foo": '"bar"'}, 'new Dictionary<string,Object>{ { "foo" , "\\"bar\\"" } }'),
        (["foo"], 'new [] { "foo" }'),
        (["foo", '"bar"'], 'new [] { "foo", "\\"bar\\"" }'),
        ([{"foo": "bar"}], 'new [] { new Dictionary<string,Object>{ { "foo" , "bar" } } }'),
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
def test_translate_type_csharp(test_input, expected):
    assert translators.CSharpTranslator.translate(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [("", '//'), ("foo", '// foo'), ("['best effort']", "// ['best effort']")],
)
def test_translate_comment_csharp(test_input, expected):
    assert translators.CSharpTranslator.comment(test_input) == expected


@pytest.mark.parametrize(
    "input_name,input_value,expected",
    [("foo", '""', 'var foo = "";'), ("foo", '"bar"', 'var foo = "bar";')],
)
def test_translate_assign_csharp(input_name, input_value, expected):
    assert translators.CSharpTranslator.assign(input_name, input_value) == expected


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"foo": "bar"}, '// Parameters\nvar foo = "bar";\n'),
        ({"foo": True}, '// Parameters\nvar foo = true;\n'),
        ({"foo": 5}, '// Parameters\nvar foo = 5;\n'),
        ({"foo": 1.1}, '// Parameters\nvar foo = 1.1;\n'),
        ({"foo": ['bar', 'baz']}, '// Parameters\nvar foo = new [] { "bar", "baz" };\n'),
        (
            {"foo": {'bar': 'baz'}},
            '// Parameters\nvar foo = new Dictionary<string,Object>{ { "bar" , "baz" } };\n',
        ),
    ],
)
def test_translate_codify_csharp(parameters, expected):
    assert translators.CSharpTranslator.codify(parameters) == expected


# Powershell section
@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("foo", '"foo"'),
        ('{"foo": "bar"}', '"{`"foo`": `"bar`"}"'),
        ({"foo": "bar"}, '@{"foo" = "bar"}'),
        ({"foo": '"bar"'}, '@{"foo" = "`"bar`""}'),
        ({"foo": ["bar"]}, '@{"foo" = @("bar")}'),
        ({"foo": {"bar": "baz"}}, '@{"foo" = @{"bar" = "baz"}}'),
        ({"foo": {"bar": '"baz"'}}, '@{"foo" = @{"bar" = "`"baz`""}}'),
        (["foo"], '@("foo")'),
        (["foo", '"bar"'], '@("foo", "`"bar`"")'),
        ([{"foo": "bar"}], '@(@{"foo" = "bar"})'),
        ([{"foo": '"bar"'}], '@(@{"foo" = "`"bar`""})'),
        (12345, '12345'),
        (-54321, '-54321'),
        (1.2345, '1.2345'),
        (-5432.1, '-5432.1'),
        (float('nan'), "[double]::NaN"),
        (float('-inf'), "[double]::NegativeInfinity"),
        (float('inf'), "[double]::PositiveInfinity"),
        (True, '$True'),
        (False, '$False'),
        (None, '$Null'),
    ],
)
def test_translate_type_powershell(test_input, expected):
    assert translators.PowershellTranslator.translate(test_input) == expected


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"foo": "bar"}, '# Parameters\n$foo = "bar"\n'),
        ({"foo": True}, '# Parameters\n$foo = $True\n'),
        ({"foo": 5}, '# Parameters\n$foo = 5\n'),
        ({"foo": 1.1}, '# Parameters\n$foo = 1.1\n'),
        ({"foo": ['bar', 'baz']}, '# Parameters\n$foo = @("bar", "baz")\n'),
        ({"foo": {'bar': 'baz'}}, '# Parameters\n$foo = @{"bar" = "baz"}\n'),
        (
            OrderedDict([['foo', 'bar'], ['baz', ['buz']]]),
            '# Parameters\n$foo = "bar"\n$baz = @("buz")\n',
        ),
    ],
)
def test_translate_codify_powershell(parameters, expected):
    assert translators.PowershellTranslator.codify(parameters) == expected


@pytest.mark.parametrize(
    "input_name,input_value,expected",
    [("foo", '""', '$foo = ""'), ("foo", '"bar"', '$foo = "bar"')],
)
def test_translate_assign_powershell(input_name, input_value, expected):
    assert translators.PowershellTranslator.assign(input_name, input_value) == expected


@pytest.mark.parametrize(
    "test_input,expected", [("", '#'), ("foo", '# foo'), ("['best effort']", "# ['best effort']")]
)
def test_translate_comment_powershell(test_input, expected):
    assert translators.PowershellTranslator.comment(test_input) == expected


# F# section
@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("foo", '"foo"'),
        ('{"foo": "bar"}', '"{\\"foo\\": \\"bar\\"}"'),
        ({"foo": "bar"}, '[ ("foo", "bar" :> IComparable) ] |> Map.ofList'),
        ({"foo": '"bar"'}, '[ ("foo", "\\"bar\\"" :> IComparable) ] |> Map.ofList'),
        (["foo"], '[ "foo" ]'),
        (["foo", '"bar"'], '[ "foo"; "\\"bar\\"" ]'),
        ([{"foo": "bar"}], '[ [ ("foo", "bar" :> IComparable) ] |> Map.ofList ]'),
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
def test_translate_type_fsharp(test_input, expected):
    assert translators.FSharpTranslator.translate(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [("", '(*  *)'), ("foo", '(* foo *)'), ("['best effort']", "(* ['best effort'] *)")],
)
def test_translate_comment_fsharp(test_input, expected):
    assert translators.FSharpTranslator.comment(test_input) == expected


@pytest.mark.parametrize(
    "input_name,input_value,expected",
    [("foo", '""', 'let foo = ""'), ("foo", '"bar"', 'let foo = "bar"')],
)
def test_translate_assign_fsharp(input_name, input_value, expected):
    assert translators.FSharpTranslator.assign(input_name, input_value) == expected


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"foo": "bar"}, '(* Parameters *)\nlet foo = "bar"\n'),
        ({"foo": True}, '(* Parameters *)\nlet foo = true\n'),
        ({"foo": 5}, '(* Parameters *)\nlet foo = 5\n'),
        ({"foo": 1.1}, '(* Parameters *)\nlet foo = 1.1\n'),
        ({"foo": ['bar', 'baz']}, '(* Parameters *)\nlet foo = [ "bar"; "baz" ]\n'),
        (
            {"foo": {'bar': 'baz'}},
            '(* Parameters *)\nlet foo = [ ("bar", "baz" :> IComparable) ] |> Map.ofList\n',
        ),
    ],
)
def test_translate_codify_fsharp(parameters, expected):
    assert translators.FSharpTranslator.codify(parameters) == expected


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


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("foo", '"foo"'),
        ('{"foo": "bar"}', '"{""foo"": ""bar""}"'),
        ({1: "foo"}, 'containers.Map({\'1\'}, {"foo"})'),
        ({1.0: "foo"}, 'containers.Map({\'1.0\'}, {"foo"})'),
        ({None: "foo"}, 'containers.Map({\'None\'}, {"foo"})'),
        ({True: "foo"}, 'containers.Map({\'True\'}, {"foo"})'),
        ({"foo": "bar"}, 'containers.Map({\'foo\'}, {"bar"})'),
        ({"foo": '"bar"'}, 'containers.Map({\'foo\'}, {"""bar"""})'),
        ({"foo": ["bar"]}, 'containers.Map({\'foo\'}, {{"bar"}})'),
        (
            {"foo": {"bar": "baz"}},
            'containers.Map({\'foo\'}, {containers.Map({\'bar\'}, {"baz"})})',
        ),
        (
            {"foo": {"bar": '"baz"'}},
            'containers.Map({\'foo\'}, {containers.Map({\'bar\'}, {"""baz"""})})',
        ),
        (["foo"], '{"foo"}'),
        (["foo", '"bar"'], '{"foo", """bar"""}'),
        ([{"foo": "bar"}], '{containers.Map({\'foo\'}, {"bar"})}'),
        ([{"foo": '"bar"'}], '{containers.Map({\'foo\'}, {"""bar"""})}'),
        (12345, '12345'),
        (-54321, '-54321'),
        (1.2345, '1.2345'),
        (-5432.1, '-5432.1'),
        (True, 'true'),
        (False, 'false'),
        (None, 'NaN'),
    ],
)
def test_translate_type_matlab(test_input, expected):
    assert translators.MatlabTranslator.translate(test_input) == expected


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"foo": "bar"}, '% Parameters\nfoo = "bar";\n'),
        ({"foo": True}, '% Parameters\nfoo = true;\n'),
        ({"foo": 5}, '% Parameters\nfoo = 5;\n'),
        ({"foo": 1.1}, '% Parameters\nfoo = 1.1;\n'),
        ({"foo": ['bar', 'baz']}, '% Parameters\nfoo = {"bar", "baz"};\n'),
        ({"foo": {'bar': 'baz'}}, '% Parameters\nfoo = containers.Map({\'bar\'}, {"baz"});\n'),
        (
            OrderedDict([['foo', 'bar'], ['baz', ['buz']]]),
            '% Parameters\nfoo = "bar";\nbaz = {"buz"};\n',
        ),
    ],
)
def test_translate_codify_matlab(parameters, expected):
    assert translators.MatlabTranslator.codify(parameters) == expected


@pytest.mark.parametrize(
    "test_input,expected", [("", '%'), ("foo", '% foo'), ("['best effort']", "% ['best effort']")]
)
def test_translate_comment_matlab(test_input, expected):
    assert translators.MatlabTranslator.comment(test_input) == expected


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
