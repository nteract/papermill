import os
import logging
import warnings

from contextlib import contextmanager
from functools import wraps

from .exceptions import PapermillParameterOverwriteWarning

logger = logging.getLogger('papermill.utils')


def any_tagged_cell(nb, tag):
    """Whether the notebook contains at least one cell tagged ``tag``?

    Parameters
    ----------
    nb : nbformat.NotebookNode
        The notebook to introspect
    tag : str
        The tag to look for

    Returns
    -------
    bool
        Whether the notebook contains a cell tagged ``tag``?
    """
    return any([tag in cell.metadata.tags for cell in nb.cells])


def find_first_tagged_cell_index(nb, tag):
    """Find the first tagged cell ``tag`` in the notebook.

    Parameters
    ----------
    nb : nbformat.NotebookNode
        The notebook to introspect
    tag : str
        The tag to look for

    Returns
    -------
    nbformat.NotebookNode
        Whether the notebook contains a cell tagged ``tag``?
    """
    parameters_indices = []
    for idx, cell in enumerate(nb.cells):
        if tag in cell.metadata.tags:
            parameters_indices.append(idx)
    if not parameters_indices:
        return -1
    return parameters_indices[0]


def merge_kwargs(caller_args, **callee_args):
    """Merge named argument.

    Function takes a dictionary of caller arguments and callee arguments as keyword arguments
    Returns a dictionary with merged arguments. If same argument is in both caller and callee
    arguments the last one will be taken and warning will be raised.

    Parameters
    ----------
    caller_args : dict
        Caller arguments
    **callee_args
        Keyword callee arguments

    Returns
    -------
    args : dict
       Merged arguments
    """
    conflicts = set(caller_args) & set(callee_args)
    if conflicts:
        args = format('; '.join(['{}={}'.format(key, value) for key, value in callee_args.items()]))
        msg = "Callee will overwrite caller's argument(s): {}".format(args)
        warnings.warn(msg, PapermillParameterOverwriteWarning)
    return dict(caller_args, **callee_args)


def remove_args(args=None, **kwargs):
    """Remove arguments from kwargs.

    Parameters
    ----------
    args : list
        Argument names to remove from kwargs
    **kwargs
        Arbitrary keyword arguments

    Returns
    -------
    kwargs : dict
       New dictionary of arguments
    """
    if not args:
        return kwargs
    return {k: v for k, v in kwargs.items() if k not in args}


# retry decorator
def retry(num):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            exception = None

            for i in range(num):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.debug('Retrying after: {}'.format(e))
                    exception = e
            else:
                raise exception

        return wrapper

    return decorate


@contextmanager
def chdir(path):
    """Change working directory to `path` and restore old path on exit.

    `path` can be `None` in which case this is a no-op.
    """
    if path is None:
        yield

    else:
        old_dir = os.getcwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(old_dir)
