import os
import shutil
import subprocess
import tempfile
import time

import nbformat

from papermill.api import read_notebook, save_notebook


def execute_notebook(notebook, output, **kwargs):
    """Executes a single notebook locally.

    Args:
        notebook (str): Path to input notebook.
        output (str): Path to save exexuted notebook.
        **kwargs: Arbitrary keyword arguments to pass to the notebook preface.

    """
    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, 'parameterized.ipynb')
    _parameterize_notebook(notebook, tmp_path, **kwargs)
    _execute_notebook(tmp_path, output)
    os.remove(tmp_path)


def _parameterize_notebook(notebook_path, output_path, **kwargs):

    if not kwargs:
        # No parameters, just copy the notebook.
        shutil.copyfile(notebook_path, output_path)
        return

    # Pull out variable names and values from the parameters argument.
    param_content = "# Parameters\n"
    for var, val in kwargs.iteritems():
        if isinstance(val, basestring):
            val = '"%s"' % val  # TODO: Handle correctly escaping input strings.
        param_content += '%s = %s\n' % (var, val)

    # Remove the first cell of the block and replace it with the param content.
    nb = read_notebook(notebook_path)

    preface_index = find_preface_index(nb)
    old_preface = nb.cells[preface_index]
    before = nb.cells[:preface_index]
    after = nb.cells[preface_index + 1:]
    newcell = nbformat.v4.new_code_cell(source=param_content)
    newcell.metadata['tags'] = old_preface.metadata.tags
    nb.cells = before + [newcell] + after

    # Apply papermill metadata
    nb.metadata.papermill['parameters'] = kwargs
    save_notebook(nb, output_path)


def _execute_notebook(notebook_path, output_path):

    t0 = time.time()
    exit_code = subprocess.call(
        ['jupyter', 'nbconvert', '--to', 'notebook',  '--execute',
         '--NbConvertApp.output_base={}'.format(notebook_path),
         '--ExecutePreprocessor.timeout=-1',
         '--ClearOutputPreprocessor.enabled=True', notebook_path]
    )

    if exit_code != 0:
        raise PapermillException("Exception encountered when trying to execute the notebook.")

    duration = time.time() - t0

    # TODO: This will be removed when we build our own "nbconvert"
    nb = read_notebook(notebook_path)

    # Record specified environment variable values.
    nb.metadata.papermill['environment_variables'] = _fetch_environment_variables()
    nb.metadata.papermill['duration'] = duration
    save_notebook(nb, output_path)


def find_preface_index(nb):
    preface_indices = []
    for idx, cell in enumerate(nb.cells):
        if "preface" in cell.metadata.tags:
            preface_indices.append(idx)
    if not preface_indices:
        raise PapermillException("No preface tag found")
    elif len(preface_indices) > 1:
        raise PapermillException("Multiple preface tags found")
    return preface_indices[0]


_execution_configuration = dict(
    environment_variables=[]
)


def set_environment_variable_names(*args):
    _execution_configuration['environment_variables'] = sorted(
        set(_execution_configuration['environment_variables']) | set(args))


def _fetch_environment_variables():
    ret = dict()
    for name, value in os.environ.iteritems():
        if name in _execution_configuration['environment_variables']:
            ret[name] = value
    return ret


class PapermillException(Exception):
    """Raised when an exception is encountered when operating on a notebook."""
