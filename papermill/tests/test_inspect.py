from pathlib import Path

import pytest

from papermill.iorw import load_notebook_node


NOTEBOOKS_PATH = Path(__file__).parent / "notebooks"


def _get_fullpath(name):
    return NOTEBOOKS_PATH / name


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
