from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click import Context

from papermill.iorw import load_notebook_node
from papermill.inspection import display_notebook_help


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
def test_default_parameters(name, expected):
    nb = load_notebook_node(str(name))

    assert nb.metadata['papermill']['default_parameters'] == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        (
            _get_fullpath("no_parameters.ipynb"),
            [
                "Dummy usage",
                "\n  Parameters inferred for notebook '{name}':",
                "\n  No cell tagged 'parameters'",
            ],
        ),
        (
            _get_fullpath("simple_execute.ipynb"),
            [
                "Dummy usage",
                "\n  Parameters inferred for notebook '{name}':",
                "     msg: Unknown type (default None)\t\t",
            ],
        ),
        (
            _get_fullpath("complex_parameters.ipynb"),
            [
                "Dummy usage",
                "\n  Parameters inferred for notebook '{name}':",
                "     msg: Unknown type (default None)\t\t",
                "     a: float (default 2.25)\t\tVariable a",
                "     b: List[str] (default ['Hello','World'])\t\tNice list",
                "     c: NoneType (default None)\t\t",
            ],
        ),
        (
            _get_fullpath("notimplemented_translator.ipynb"),
            [
                "Dummy usage",
                "\n  Parameters inferred for notebook '{name}':",
                "\n  Can't infer anything about this notebook's parameters. It may not have any parameter defined.",  # noqa
            ],
        ),
    ],
)
def test_display_notebook_help(click_context, name, expected):
    with patch("papermill.inspection.click.echo") as echo:
        display_notebook_help(click_context, str(name))
        print(echo.call_args_list)
        assert echo.call_count == len(expected)
        for call, target in zip(echo.call_args_list, expected):
            assert call[0][0] == target.format(name=str(name))
