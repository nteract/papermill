import os

import pandas as pd
import IPython
from IPython.display import display as ip_display, Markdown
from six import string_types

from papermill.exceptions import PapermillException
from papermill.iorw import load_notebook_node, list_notebook_files


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
    """
    Displays an object with the reference 'name'.

    Args:
        name (str): Name of the output.
        obj: An object that can be displayed in the notebook.

    """
    data, metadata = IPython.core.formatters.format_display_data(obj)
    metadata['papermill'] = dict(name=name)
    ip_display(data, metadata=metadata, raw=True)


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
            "Notebooks should have an '.ipynb' file extension. Provided path: '%s'", path)

    nb = Notebook()
    nb.path = path
    nb.node = load_notebook_node(path)
    return nb


def read_notebooks(path):
    """
    Returns a NotebookCollection loaded from the notebooks found the in the directory specified by 'path'.

    Args:
        path (str): Path to directory containing notebook ".ipynb" files.

    Returns:
        A NotebookCollection object.
    """
    nbs = NotebookCollection()
    for notebook_path in list_notebook_files(path):
        fn = os.path.basename(notebook_path)
        nbs[fn] = read_notebook(notebook_path)
    return nbs


class Notebook(object):

    def __init__(self):

        self.path = ''
        self.node = None

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
        return _get_papermill_metadata(self.node, 'environment_variables', default={})

    @property
    def data(self):
        return _fetch_notebook_data(self.node)

    @property
    def dataframe(self):
        df = pd.DataFrame(columns=['name', 'value', 'type', 'filename'])

        i = 0
        for name in sorted(self.parameters.keys()):
            df.loc[i] = name, self.parameters[name], 'parameter', self.filename
            i += 1

        for name in sorted(self.data.keys()):
            df.loc[i] = name, self.data[name], 'record', self.filename
            i += 1
        return df

    def display_output(self, name):
        """Display the output from this notebook in the running notebook."""
        outputs = _get_notebook_outputs(self.node)
        if name not in outputs:
            raise PapermillException("Output Name '%s' is not available in this notebook.")
        output = outputs[name]
        ip_display(output.data, metadata=output.metadata, raw=True)


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

    def __init__(self):

        self._notebooks = {}

    def __setitem__(self, key, value):
        # If notebook is a path str then load the notebook.
        if isinstance(value, string_types):
            value = read_notebook(value)

        if not isinstance(value, Notebook):
            raise PapermillException(
                "Value must either be a path string or a Papermill Notebook object. Found: '%s'" % str(type(value)))
        self._notebooks[key] = value

    def __getitem__(self, key):
        return self._notebooks[key]

    def __delitem__(self, key):
        del self._notebooks[key]

    @property
    def dataframe(self):
        dfs = []
        for key in sorted(self._notebooks):
            nb = self._notebooks[key]
            df = nb.dataframe
            df['key'] = key
            dfs.append(df)
        return pd.concat(dfs).reset_index(drop=True)

    def display_output(self, key, output_name):
        if isinstance(key, string_types):
            ip_display(Markdown("### %s" % str(key)))
            self[key].display_output(output_name)
        else:
            for i, k in enumerate(key):
                if i > 0:
                    # between outputs
                    ip_display(Markdown("<hr>"))
                ip_display(Markdown("### %s" % str(k)))
                self[k].display_output(output_name)
