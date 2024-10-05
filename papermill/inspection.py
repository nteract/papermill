"""Deduce parameters of a notebook from the parameters cell."""
from pathlib import Path

import click

from .iorw import get_pretty_path, load_notebook_node, local_file_io_cwd
from .log import logger
from .parameterize import add_builtin_parameters, parameterize_path
from .translators import papermill_translators
from .utils import any_tagged_cell, find_first_tagged_cell_index, nb_kernel_name, nb_language


def _open_notebook(notebook_path, parameters):
    path_parameters = add_builtin_parameters(parameters)
    input_path = parameterize_path(notebook_path, path_parameters)
    logger.info(f"Input Notebook:  {get_pretty_path(input_path)}")

    with local_file_io_cwd():
        return load_notebook_node(input_path)


def _infer_parameters(nb, name=None, language=None):
    """Infer the notebook parameters.

    Parameters
    ----------
    nb : nbformat.NotebookNode
        Notebook

    Returns
    -------
    List[Parameter]
       List of parameters (name, inferred_type_name, default, help)
    """
    params = []

    parameter_cell_idx = find_first_tagged_cell_index(nb, "parameters")
    if parameter_cell_idx < 0:
        return params
    parameter_cell = nb.cells[parameter_cell_idx]

    kernel_name = nb_kernel_name(nb, name)
    language = nb_language(nb, language)

    translator = papermill_translators.find_translator(kernel_name, language)
    try:
        params = translator.inspect(parameter_cell)
    except NotImplementedError:
        logger.warning(f"Translator for '{language}' language does not support parameter introspection.")

    return params


def display_notebook_help(ctx, notebook_path, parameters):
    """Display help on notebook parameters.

    Parameters
    ----------
    ctx : click.Context
        Click context
    notebook_path : str
        Path to the notebook to be inspected
    """
    nb = _open_notebook(notebook_path, parameters)
    click.echo(ctx.command.get_usage(ctx))
    pretty_path = get_pretty_path(notebook_path)
    click.echo(f"\nParameters inferred for notebook '{pretty_path}':")

    if not any_tagged_cell(nb, "parameters"):
        click.echo("\n  No cell tagged 'parameters'")
        return 1

    params = _infer_parameters(nb)
    if params:
        for param in params:
            p = param._asdict()
            type_repr = p["inferred_type_name"]
            if type_repr == "None":
                type_repr = "Unknown type"

            definition = f"  {p['name']}: {type_repr} (default {p['default']})"
            if len(definition) > 30:
                if len(p["help"]):
                    param_help = f"{definition}\n{34 * ' '}{p['help']}"
                else:
                    param_help = definition
            else:
                param_help = f"{definition:<34}{p['help']}"
            click.echo(param_help)
    else:
        click.echo(
            "\n  Can't infer anything about this notebook's parameters. " "It may not have any parameter defined."
        )

    return 0


def inspect_notebook(notebook_path, parameters=None):
    """Return the inferred notebook parameters.

    Parameters
    ----------
    notebook_path : str or Path
        Path to notebook
    parameters : dict, optional
        Arbitrary keyword arguments to pass to the notebook parameters

    Returns
    -------
    Dict[str, Parameter]
       Mapping of (parameter name, {name, inferred_type_name, default, help})
    """
    if isinstance(notebook_path, Path):
        notebook_path = str(notebook_path)

    nb = _open_notebook(notebook_path, parameters)

    params = _infer_parameters(nb)
    return {p.name: p._asdict() for p in params}
