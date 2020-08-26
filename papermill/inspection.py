# -*- coding: utf-8 -*-
"""
Deduce parameters of a notebook from the parameters cell.
"""
import click

from .iorw import get_pretty_path, open_notebook
from .utils import any_tagged_cell


def display_notebook_help(ctx, notebook_path):
    """Display help on notebook parameters.

    Parameters
    ----------
    ctx : click.Context
        Click context
    notebook_path : str
        Path to the notebook to be inspected
    """
    nb = open_notebook(notebook_path)
    click.echo(ctx.command.get_usage(ctx))
    pretty_path = get_pretty_path(notebook_path)
    click.echo("\n  Parameters inferred for notebook '{}':".format(pretty_path))

    if not any_tagged_cell(nb, "parameters"):
        click.echo("\n  No cell tagged 'parameters'")
        return

    params = nb.metadata['papermill']['default_parameters']
    if params:
        for p in params.values():
            type_repr = p["inferred_type_name"]
            if type_repr == "None":
                type_repr = "Unknown type"
            click.echo(
                "     {}: {} (default {})\t\t{}".format(p["name"], type_repr, p["default"], p["help"])
            )
    else:
        click.echo(
            "\n  Can't infer anything about this notebook's parameters. "
            "It may not have any parameter defined."
        )
