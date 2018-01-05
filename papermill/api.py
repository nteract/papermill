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

RECORD_OUTPUT_TYPE = 'application/papermill.record+json'
DISPLAY_OUTPUT_TYPE = 'application/papermill.display+json'


def record(name, value):
    """
    Records the value as part of the executing cell's output to be retrieved
    during inspection.

    Args:
        name (str): Name of the value
        value: The value to record.

    """
    # IPython.display.display takes a tuple of objects as first parameter
    # `http://ipython.readthedocs.io/en/stable/api/generated/IPython.display.html#IPython.display.display`
    ip_display(data={RECORD_OUTPUT_TYPE: {name: value}}, raw=True)


def display(name, obj):
    """
    Displays an object with the reference 'name'.

    Args:
        name (str): Name of the output.
        obj: An object that can be displayed in the notebook.

    """
    data, metadata = IPython.core.formatters.format_display_data(obj)
    metadata['papermill'] = dict(name=name)
    ip_display(data=data, metadata=metadata, raw=True)


def read_notebook(path):
    """
    Returns a Notebook object loaded from the location specified at 'path'.

    Args:
        path (str): Path to notebook ".ipynb" file.

    Returns:
        A Notebook object.

    """
    if not path.endswith(".ipynb"):
        raise PapermillException(
            "Requires an '.ipynb' file extension. Provided path: '%s'",
            path)

    nb = Notebook()
    nb.path = path
    nb.node = load_notebook_node(path)
    return nb


def read_notebooks(path):
    """
    Returns a NotebookCollection loaded from the notebooks found the in the
    directory specified by 'path'.

    Args:
        path (str): Path to directory containing notebook ".ipynb" files.

    Returns:
        A NotebookCollection object.

    """
    nb_collection = NotebookCollection()
    for notebook_path in list_notebook_files(path):
        fn = os.path.basename(notebook_path)
        nb_collection[fn] = read_notebook(notebook_path)
    return nb_collection


class Notebook(object):
    """
    Representation of a notebook.

    Constructor args:
        node (nbformat.NotebookNode): a notebook object
        path (str): the path to the notebook (optional)

    """
    def __init__(self, node=None, path=None):

        if path is not None and not node:
            raise ValueError('notebook must be defined when path is given')
        self.path = path or ''
        self.node = node

    @property
    def filename(self):
        return os.path.basename(self.path)

    @property
    def directory(self):
        return os.path.dirname(self.path)

    @property
    def version(self):
        return _get_papermill_metadata(self.node, 'version', default=None)

    @property
    def parameters(self):
        return _get_papermill_metadata(self.node, 'parameters', default={})

    @property
    def environment_variables(self):
        return _get_papermill_metadata(
            self.node, 'environment_variables', default={})

    @property
    def data(self):
        return _fetch_notebook_data(self.node)

    @property
    def dataframe(self):
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
        df = pd.DataFrame(columns=['filename', 'cell', 'value', 'type'])

        for i, cell in enumerate(self.node.cells):
            execution_count = cell.get("execution_count")
            if not execution_count:
                continue
            name = "Out [%s]" % str(execution_count)
            value = cell.metadata.get('papermill', {}).get('duration', 0.0)
            df.loc[i] = self.filename, name, value, "time (s)",
        return df

    def display_output(self, name):
        """Display output from a source notebook in the running notebook.

        Parameter:
            name (str): source notebook

        """
        outputs = _get_notebook_outputs(self.node)
        if name not in outputs:
            raise PapermillException(
                "Output Name '%s' is not available in this notebook.")
        output = outputs[name]
        ip_display(data=output.data, metadata=output.metadata, raw=True)


def _get_papermill_metadata(nb, name, default=None):
    return nb.metadata.get('papermill', {}).get(name, default)


def _get_notebook_outputs(nb_node):
    outputs = {}
    for cell in nb_node.cells:
        for output in cell.get('outputs', []):
            if 'papermill' in output.get('metadata', {}):
                output_name = output.metadata.papermill.get('name')
                if output_name:
                    outputs[output_name] = output
    return outputs


def _fetch_notebook_data(nb_node):
    """Returns the data recorded in a notebook."""
    ret = {}
    for cell in nb_node.cells:
        for output in cell.get('outputs', []):
            if 'data' in output and RECORD_OUTPUT_TYPE in output['data']:
                ret.update(output['data'][RECORD_OUTPUT_TYPE])
    return ret


class NotebookCollection(object):
    """Represents a collection of notebooks"""
    def __init__(self):

        self._notebooks = {}

    def __setitem__(self, key, value):
        # If notebook is a path str then load the notebook.
        if isinstance(value, string_types):
            value = read_notebook(value)

        if not isinstance(value, Notebook):
            raise PapermillException(
                "Value must either be a path string or a Papermill Notebook object. Found: '%s'"
                % str(type(value)))
        self._notebooks[key] = value

    def __getitem__(self, key):
        return self._notebooks[key]

    def __delitem__(self, key):
        del self._notebooks[key]

    @property
    def dataframe(self):
        df_list = []
        for key in sorted(self._notebooks):
            nb = self._notebooks[key]
            df = nb.dataframe
            df['key'] = key
            df_list.append(df)
        return pd.concat(df_list).reset_index(drop=True)

    @property
    def metrics(self):
        df_list = []
        for key in sorted(self._notebooks):
            nb = self._notebooks[key]
            df = nb.metrics
            df['key'] = key
            df_list.append(df)
        return pd.concat(df_list).reset_index(drop=True)

    def display_output(self, key, output_name):
        """Display markdown of output"""
        if isinstance(key, string_types):
            ip_display(Markdown("### %s" % str(key)))
            self[key].display_output(output_name)
        else:
            for i, k in enumerate(key):
                if i > 0:
                    ip_display(Markdown("<hr>"))  # tag between outputs
                ip_display(Markdown("### %s" % str(k)))
                self[k].display_output(output_name)
