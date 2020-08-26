 # -*- coding: utf-8 -*-
"""
Deduce parameters of a notebook from the parameters cell.
"""

import ast

import click

from .iorw import get_pretty_path, open_notebook
from .models import Parameter
from .parameterize import find_first_tagged_cell_index
from .translators import papermill_translators


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
    click.echo("")
    click.echo("  Parameters inferred for notebook '{}':".format(pretty_path))
    
    parameter_cell_idx = find_first_tagged_cell_index(nb, "parameters")
    if parameter_cell_idx < 0:
        click.echo("\n  No cell tagged 'parameters'")
        return
    
    parameter_cell = nb.cells[parameter_cell_idx]
    kernel_name = nb.metadata.kernelspec.name
    language = nb.metadata.kernelspec.language

    translator = papermill_translators.find_translator(kernel_name, language)
    params = translator.inspect(parameter_cell)
    if params:
        for p in params:
            type_repr = p.inferred_type_name if p.inferred_type_name != "None" else "Unknown type"
            click.echo("     {}: {} (default {})\t{}".format(p.name, type_repr, p.default, p.help))
    else:
        click.echo("  Can't infer anything about this notebook's parameters")
