# -*- coding: utf-8 -*-
"""
api.py

Provides the API for papermill

"""
from __future__ import unicode_literals
import os

import IPython
from IPython.display import display as ip_display, Markdown
import pandas as pd
from six import string_types

from .exceptions import PapermillException
from .iorw import load_notebook_node, list_notebook_files
from .utils import deprecated

RECORD_OUTPUT_TYPE = 'application/papermill.record+json'
DISPLAY_OUTPUT_TYPE = 'application/papermill.display+json'


@deprecated('1.0.0', '`scrapbook.glue` (nteract-scrapbook)')
def record(name, value):
    """
    Record a value in the output notebook when a cell is executed.

    The recorded value can be retrieved during later inspection of the
    output notebook.

    Example
    -------
    `record` provides a handy way for data to be stored with a notebook to
    be used later::

        pm.record("hello", "world")
        pm.record("number", 123)
        pm.record("some_list", [1, 3, 5])
        pm.record("some_dict", {"a": 1, "b": 2})

    pandas can be used later to recover recorded values by
    reading the output notebook into a `dataframe`::

        nb = pm.read_notebook('notebook.ipynb')
        nb.dataframe

    Parameters
    ----------
    name : str
        Name of the value to record.
    value: str, int, float, list, dict
        The value to record.

    """
    # IPython.display.display takes a tuple of objects as first parameter
    # `http://ipython.readthedocs.io/en/stable/api/generated/IPython.display.html#IPython.display.display`
    data = {RECORD_OUTPUT_TYPE: {name: value}}
    ip_display(data, raw=True)


@deprecated('1.0.0', '`scrapbook.glue` (nteract-scrapbook)')
def display(name, obj):
    """
    Display an object with the reference `name`.

    Parameters
    ----------
    name : str
        Name of the output.
    obj : object
        An object that can be displayed in the notebook.

    """
    data, metadata = IPython.core.formatters.format_display_data(obj)
    metadata['papermill'] = dict(name=name)
    ip_display(data, metadata=metadata, raw=True)


@deprecated('1.0.0', '`scrapbook.read_notebook` (nteract-scrapbook)')
def read_notebook(path):
    """
    Returns a Notebook object loaded from the location specified at `path`.

    Parameters
    ----------
    path : str
        Path to a notebook `.ipynb` file.

    Returns
    -------
    notebook : object
        A Notebook object.

    """
    if not path.endswith(".ipynb"):
        raise PapermillException("Requires an '.ipynb' file extension. Provided path: '%s'", path)

    nb = Notebook()
    nb.path = path
    nb.node = load_notebook_node(path)
    return nb


@deprecated('1.0.0', '`scrapbook.read_notebooks` (nteract-scrapbook)')
def read_notebooks(path):
    """
    Returns a NotebookCollection including the notebooks read from the
    directory specified by `path`.

    Parameters
    ----------
    path : str
        Path to directory containing notebook `.ipynb` files.

    Returns
    -------
    nb_collection : object
        A `NotebookCollection` object.

    """
    nb_collection = NotebookCollection()
    for notebook_path in list_notebook_files(path):
        fn = os.path.basename(notebook_path)
        nb_collection[fn] = read_notebook(notebook_path)
    return nb_collection


class Notebook(object):
    """
    Representation of a notebook.

    Parameters
    ----------
    node : `nbformat.NotebookNode`
        a notebook object
    path : str, optional
        the path to the notebook
    """

    def __init__(self, node=None, path=None):

        if path is not None and not node:
            raise ValueError('notebook must be defined when path is given')
        self.path = path or ''
        self.node = node

    @property
    def filename(self):
        """str: filename found a the specified path"""
        return os.path.basename(self.path)

    @property
    def directory(self):
        """str: directory name at the specified path"""
        return os.path.dirname(self.path)

    @property
    def version(self):
        """str: version of Jupyter notebook spec"""
        return _get_papermill_metadata(self.node, 'version', default=None)

    @property
    def parameters(self):
        """dict: parameters stored in the notebook metadata"""
        return _get_papermill_metadata(self.node, 'parameters', default={})

    @property
    def environment_variables(self):
        """dict: environment variables used by the notebook execution"""
        return _get_papermill_metadata(self.node, 'environment_variables', default={})

    @property
    def data(self):
        """dict: a dictionary of data found in the notebook"""
        return _fetch_notebook_data(self.node)

    @property
    def dataframe(self):
        """pandas dataframe: a dataframe of named parameters and values"""
        df = pd.DataFrame(columns=['name', 'value', 'type', 'filename'])

        # TODO: refactor to a Dict comprehension or list comprehensions
        i = 0
        for name in sorted(self.parameters.keys()):
            df.loc[i] = name, self.parameters[name], 'parameter', self.filename
            i += 1

        for name in sorted(self.data.keys()):
            df.loc[i] = name, self.data[name], 'record', self.filename
            i += 1
        return df

    @property
    def metrics(self):
        """pandas dataframe: dataframe of cell execution counts and times"""
        df = pd.DataFrame(columns=['filename', 'cell', 'value', 'type'])

        for i, cell in enumerate(self.node.cells):
            execution_count = cell.get("execution_count")
            if not execution_count:
                continue
            name = "Out [%s]" % str(execution_count)
            value = cell.metadata.get('papermill', {}).get('duration', 0.0)
            df.loc[i] = self.filename, name, value, "time (s)"
        return df

    def display_output(self, name):
        """Display output from a named source notebook in a running notebook.

        Parameters
        ----------
        name : str
            name of source notebook

        """
        outputs = _get_notebook_outputs(self.node)
        if name not in outputs:
            raise PapermillException("Output Name '%s' is not available in this notebook." % name)
        output = outputs[name]
        ip_display(output.data, metadata=output.metadata, raw=True)


def _get_papermill_metadata(nb, name, default=None):
    """Returns a dictionary of a notebook's metadata."""
    return nb.metadata.get('papermill', {}).get(name, default)


def _get_notebook_outputs(nb_node):
    """Returns a dictionary of the notebook outputs."""
    outputs = {}
    for cell in nb_node.cells:
        for output in cell.get('outputs', []):
            if 'papermill' in output.get('metadata', {}):
                output_name = output.metadata.papermill.get('name')
                if output_name:
                    outputs[output_name] = output
    return outputs


def _fetch_notebook_data(nb_node):
    """Returns a dictionary of the data recorded in a notebook."""
    notebook_data = {}
    for cell in nb_node.cells:
        for output in cell.get('outputs', []):
            if 'data' in output and RECORD_OUTPUT_TYPE in output['data']:
                notebook_data.update(output['data'][RECORD_OUTPUT_TYPE])
    return notebook_data


class NotebookCollection(object):
    """Represents a collection of notebooks as a dictionary of notebooks.

    """

    def __init__(self):

        self._notebooks = {}

    def __setitem__(self, key, value):
        # If notebook is a path str then load the notebook.
        if isinstance(value, string_types):
            value = read_notebook(value)

        if not isinstance(value, Notebook):
            raise PapermillException(
                "Value must either be a path string or a Papermill Notebook object. Found: '%s'"
                % str(type(value))
            )
        self._notebooks[key] = value

    def __getitem__(self, key):
        return self._notebooks[key]

    def __delitem__(self, key):
        del self._notebooks[key]

    @property
    def dataframe(self):
        """list: a list of dataframes from a collection of notebooks"""
        df_list = []
        for key in sorted(self._notebooks):
            nb = self._notebooks[key]
            df = nb.dataframe
            df['key'] = key
            df_list.append(df)
        return pd.concat(df_list).reset_index(drop=True)

    @property
    def metrics(self):
        """list: a list of metrics from a collection of notebooks"""
        df_list = []
        for key in sorted(self._notebooks):
            nb = self._notebooks[key]
            df = nb.metrics
            df['key'] = key
            df_list.append(df)
        return pd.concat(df_list).reset_index(drop=True)

    def display_output(self, key, output_name):
        """Display output as markdown.

        Parameters
        ----------
        key : str
            parameter names to be used as markdown headings in output
        output_name : str
            a named notebook to display as output

        """
        if isinstance(key, string_types):
            ip_display(Markdown("### %s" % str(key)))
            self[key].display_output(output_name)
        else:
            for i, k in enumerate(key):
                if i > 0:
                    ip_display(Markdown("<hr>"))  # tag between outputs
                ip_display(Markdown("### %s" % str(k)))
                self[k].display_output(output_name)
