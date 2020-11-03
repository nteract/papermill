from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click import Context

from papermill.inspection import display_notebook_help, inspect_notebook


NOTEBOOKS_PATH = Path(__file__).parent / "notebooks"


def _get_fullpath(name):
    return NOTEBOOKS_PATH / name


@pytest.fixture
def click_context():
    mock = MagicMock(spec=Context, command=MagicMock())
    mock.command.get_usage.return_value = "Dummy usage"
    return mock


@pytest.mark.parametrize(
    "name, expected",
    [
        (_get_fullpath("no_parameters.ipynb"), {}),
        (
            _get_fullpath("simple_execute.ipynb"),
            {"msg": {"name": "msg", "inferred_type_name": "None", "default": "None", "help": ""}},
        ),
        (
            _get_fullpath("complex_parameters.ipynb"),
            {
                "msg": {"name": "msg", "inferred_type_name": "None", "default": "None", "help": ""},
                "a": {
                    "name": "a",
                    "inferred_type_name": "float",
                    "default": "2.25",
                    "help": "Variable a",
                },
                "b": {
                    "name": "b",
                    "inferred_type_name": "List[str]",
                    "default": "['Hello','World']",
                    "help": "Nice list",
                },
                "c": {"name": "c", "inferred_type_name": "NoneType", "default": "None", "help": ""},
            },
        ),
        (_get_fullpath("notimplemented_translator.ipynb"), {}),
    ],
)
def test_inspect_notebook(name, expected):
    assert inspect_notebook(name) == expected


def test_str_path():
    expected = {"msg": {"name": "msg", "inferred_type_name": "None", "default": "None", "help": ""}}
    assert inspect_notebook(str(_get_fullpath("simple_execute.ipynb"))) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        (
            _get_fullpath("no_parameters.ipynb"),
            [
                "Dummy usage",
                "\nParameters inferred for notebook '{name}':",
                "\n  No cell tagged 'parameters'",
            ],
        ),
        (
            _get_fullpath("simple_execute.ipynb"),
            [
                "Dummy usage",
                "\nParameters inferred for notebook '{name}':",
                "  msg: Unknown type (default None)",
            ],
        ),
        (
            _get_fullpath("complex_parameters.ipynb"),
            [
                "Dummy usage",
                "\nParameters inferred for notebook '{name}':",
                "  msg: Unknown type (default None)",
                "  a: float (default 2.25)         Variable a",
                "  b: List[str] (default ['Hello','World'])\n                                  Nice list",  # noqa
                "  c: NoneType (default None)      ",
            ],
        ),
        (
            _get_fullpath("notimplemented_translator.ipynb"),
            [
                "Dummy usage",
                "\nParameters inferred for notebook '{name}':",
                "\n  Can't infer anything about this notebook's parameters. It may not have any parameter defined.",  # noqa
            ],
        ),
    ],
)
def test_display_notebook_help(click_context, name, expected):
    with patch("papermill.inspection.click.echo") as echo:
        display_notebook_help(click_context, str(name), None)

        assert echo.call_count == len(expected)
        for call, target in zip(echo.call_args_list, expected):
            assert call[0][0] == target.format(name=str(name))
