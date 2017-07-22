import os

import pandas as pd
import IPython
from IPython.display import display as ip_display
from six import string_types

from papermill.iorw import read_notebook


RECORD_OUTPUT_TYPE = 'application/papermill.record+json'
DISPLAY_OUTPUT_TYPE = 'application/papermill.display+json'


def record(name, value):
    """
    Records the value as part of the executing cell's output to be retrieved during inspection.

    Args:
        name (str): Name of the value
        value: The value to record.

    """
    ip_display({RECORD_OUTPUT_TYPE: {name: value}}, raw=True)


def display(name, obj):
    data, metadata = IPython.core.formatters.format_display_data(obj)
    metadata['papermill'] = dict(name=name)
    ip_display(data, metadata=metadata, raw=True)


class Notebook(object):

    def __init__(self):

        self.path = ''
        self._nb_node = None

    @classmethod
    def read(cls, path):
        obj = cls()
        obj.path = path
        obj._nb_node = read_notebook(path)
        return obj

    @property
    def filename(self):
        return os.path.basename(self.path)

    @property
    def directory(self):
        return os.path.dirname(self.path)

    @property
    def nb_node(self):
        return self._nb_node

    @property
    def parameters(self):
        return _get_papermill_metadata(self._nb_node, 'parameters', default={})

    @property
    def environment_variables(self):
        return _get_papermill_metadata(self._nb_node, 'environment_variables', default={})

    @property
    def duration(self):
        return _get_papermill_metadata(self._nb_node, 'duration')

    @property
    def data(self):
        return _fetch_notebook_data(self._nb_node)

    @property
    def dataframe(self):
        """Return dataframe in 'tall' format for this notebook."""
        df = pd.DataFrame(columns=['name', 'value', 'type', 'filename'])

        i = 0
        for i, name in enumerate(sorted(self.parameters.keys()), start=i):
            df.loc[i] = name, self.parameters[name], 'parameter', self.filename

        for i, name in enumerate(sorted(self.data.keys()), start=i):
            df.loc[i] = name, self.data[name], 'record', self.filename
        return df

    def display_output(self, name):
        """Display the output from this notebook in the running notebook."""
        output = _get_notebook_output(self._nb_node, name)
        ip_display(output.data, metadata=output.metadata, raw=True)


def _get_papermill_metadata(nb, name, default=None):
    return nb.metadata.get('papermill', {}).get(name, default)


def _get_notebook_output(nb_node, name):
    outputs = {}
    for cell in nb_node.cells:
        for output in cell.get('outputs', []):
            if 'papermill' in output.metadata:
                output_name = output.metadata.papermill.get('name')
                if output_name:
                    outputs[output_name] = output
    return outputs[name]


def _fetch_notebook_data(nb_node):
    """Returns the data recorded in a notebook."""
    ret = {}
    for cell in nb_node.cells:
        for output in cell.get('outputs', []):
            if 'data' in output and RECORD_OUTPUT_TYPE in output['data']:
                ret.update(output['data'][RECORD_OUTPUT_TYPE])
    return ret


class NotebookCollection(object):

    def __init__(self):

        self._notebooks = {}

    def __setitem__(self, key, value):
        assert isinstance(value, Notebook), "Value must be type Notebook."
        self._notebooks[key] = value

    def __getitem__(self, key):
        return self._notebooks[key]

    def __delitem__(self, key):
        del self._notebooks[key]

    def __iter__(self):

        for name in sorted(self._notebooks):
            yield self[name]

    @classmethod
    def from_directory(cls, path):
        obj = cls()
        for filename in os.listdir(path):
            notebook_path = os.path.join(path, filename)
            if notebook_path.endswith('.ipynb'):
                obj[filename] = Notebook.read(notebook_path)
        return obj

    @property
    def dataframe(self):
        return pd.concat([nb.dataframe for nb in self]).reset_index(drop=True)

    def add_notebook(self, notebook, key_name=None):

        # If notebook is a path str then load the notebook.
        if isinstance(notebook, string_types):
            notebook = Notebook.read(notebook)

        key_name = key_name or notebook.filename
        self[key_name] = notebook

    def display_output(self, filename, output_name):
        self[filename].display_output(output_name)
