# -*- coding: utf-8 -*-
"""Deduce parameters of a notebook from the parameters cell."""
import click

from .iorw import get_pretty_path, load_notebook_node, local_file_io_cwd
from .log import logger
from .parameterize import add_builtin_parameters, parameterize_path
from .utils import any_tagged_cell


def _open_notebook(notebook_path, parameters):
    path_parameters = add_builtin_parameters(parameters)
    input_path = parameterize_path(notebook_path, path_parameters)
    logger.info("Input Notebook:  %s" % get_pretty_path(input_path))

    with local_file_io_cwd():
        return load_notebook_node(input_path)


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
    click.echo("\nParameters inferred for notebook '{}':".format(pretty_path))

    if not any_tagged_cell(nb, "parameters"):
        click.echo("\n  No cell tagged 'parameters'")
        return

    params = nb.metadata['papermill']['default_parameters']
    if params:
        for p in params.values():
            type_repr = p["inferred_type_name"]
            if type_repr == "None":
                type_repr = "Unknown type"

            definition = "  {}: {} (default {})".format(p["name"], type_repr, p["default"])
            if len(definition) > 30:
                if len(p["help"]):
                    param_help = "".join((definition, "\n", 34 * " ", p["help"]))
                else:
                    param_help = definition
            else:
                param_help = "{:<34}{}".format(definition, p["help"])
            click.echo(param_help)
    else:
        click.echo(
            "\n  Can't infer anything about this notebook's parameters. "
            "It may not have any parameter defined."
        )


def inspect_notebook(notebook_path, parameters=None):
    """Return the inferred notebook parameters.

    Parameters
    ----------
    notebook_path : str
        Path to notebook
    parameters : dict, optional
        Arbitrary keyword arguments to pass to the notebook parameters

    Returns
    -------
    Dict[str, Parameter]
       Mapping of (parameter name, {name, inferred_type_name, default, help})
    """
    nb = _open_notebook(notebook_path, parameters)

    return nb.metadata['papermill']['default_parameters']
