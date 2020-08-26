# -*- coding: utf-8 -*-
"""
Deduce parameters of a notebook from the parameters cell.
"""
import click

from .iorw import get_pretty_path, open_notebook
from .utils import any_tagged_cell


def display_notebook_help(notebook_path):
    """
    We make a separate function here with --help available to enable
    the same automatic error messaging, but with the ability to hijack
    the normal help messaging for when a user types `--help` on an
    input notebook

    Parameters
    ----------
    notebook_path : str
        Path to the notebook to be inspected
    """
    nb = open_notebook(notebook_path)
    pretty_path = get_pretty_path(notebook_path)
    click.echo("Usage: papermill [OPTIONS] {} [OUTPUT_PATH]".format(pretty_path))
    click.echo("\n  Parameters inferred for notebook '{}':".format(pretty_path))

    if not any_tagged_cell(nb, "parameters"):
        click.echo("\n  No cell tagged 'parameters'")
        return

    params = nb.metadata['papermill']['default_parameters']
    if params:
        for p in params:
            type_repr = p.inferred_type_name if p.inferred_type_name != "None" else "Unknown type"
            click.echo("     {}: {} (default {})\t\t{}".format(p.name, type_repr, p.default, p.help))
    else:
        click.echo("\n  Can't infer anything about this notebook's parameters. It may not have any parameter defined.")
