import logging
import os
import re
import warnings
from contextlib import contextmanager
from functools import wraps

from .exceptions import PapermillParameterOverwriteWarning

logger = logging.getLogger('papermill.utils')


SENSITIVE_PARAMETER_PATTERNS = [
    r"(?i)pass(word|wd)",
    r"(?i)pwd$",
    # A short keyword that may match many keywords unintentionally
    # is only targeted when placed at the end of the string.
    r"(?i)pass$",
    r"(?i)token",
    r"(?i)secret",
    r"(?i)authorization",
    r"(?i)auth$",
    r"(?i)key$",
    r"(?i)access_key",
    r"(?i)secret_key",
    r"(?i)private_key",
]


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


def nb_kernel_name(nb, name=None):
    """Helper for fetching out the kernel name from a notebook object.

    Parameters
    ----------
    nb : nbformat.NotebookNode
        The notebook to introspect
    name : str
        A provided name field

    Returns
    -------
    str
        The name of the kernel

    Raises
    ------
    ValueError
        If no kernel name is found or provided
    """
    name = name or nb.metadata.get('kernelspec', {}).get('name')
    if not name:
        raise ValueError("No kernel name found in notebook and no override provided.")
    return name


def nb_language(nb, language=None):
    """Helper for fetching out the programming language from a notebook object.

    Parameters
    ----------
    nb : nbformat.NotebookNode
        The notebook to introspect
    language : str
        A provided language field

    Returns
    -------
    str
        The programming language of the notebook

    Raises
    ------
    ValueError
        If no notebook language is found or provided
    """
    language = language or nb.metadata.get('language_info', {}).get('name')
    if not language:
        # v3 language path for old notebooks that didn't convert cleanly
        language = language or nb.metadata.get('kernelspec', {}).get('language')
    if not language:
        raise ValueError("No language found in notebook and no override provided.")
    return language


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
        args = format('; '.join([f'{key}={value}' for key, value in callee_args.items()]))
        msg = f"Callee will overwrite caller's argument(s): {args}"
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
                    logger.debug(f'Retrying after: {e}')
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

def obfuscate_parameter(
    name,
    value,
    name_patterns=None,
    obfuscated_value="********",
):
    """Obfuscate parameter if it is sensitive.

    Parameters
    ----------
    name : str
        The name of the parameter
    value : str
        The value of the parameter
    name_patterns : list, optional
        List of patterns to obfuscate in the notebook. Defaults to `DEFAULT_OBFUSCATE_PATTERNS`
    obfuscated_value : str, optional
        The value to replace the sensitive parameter with. Defaults to "********"

    Returns
    -------
    str
        The obfuscated value if the parameter is sensitive, otherwise the original value
    """
    if name_patterns is None:
        name_patterns = SENSITIVE_PARAMETER_PATTERNS

    if len(name_patterns) == 0:
        raise ValueError("No name patterns provided to obfuscate")
    if not value:
        # Return empty string if value is empty to show that the parameter is empty
        return value
    if any(re.search(pattern, name) for pattern in name_patterns):
        return obfuscated_value
    return value

def obfuscate_parameters(params, name_patterns=None, obfuscated_value="********"):
    """Obfuscate parameters if they are sensitive.

    Parameters
    ----------
    params : dict
        The parameters to obfuscate
    name_patterns : list, optional
        List of patterns to obfuscate in the notebook. Defaults to `DEFAULT_OBFUSCATE_PATTERNS`
    obfuscated_value : str, optional
        The value to replace the sensitive parameter with. Defaults to "********"

    Returns
    -------
    dict
        The obfuscated parameters
    """
    return {
        name: obfuscate_parameter(name, value, name_patterns, obfuscated_value)
        for name, value in params.items()
    }
