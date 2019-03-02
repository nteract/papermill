import os
import logging
import warnings
import functools

from contextlib import contextmanager
from functools import wraps

from .version import version as pm_version

logger = logging.getLogger('papermill.utils')


def deprecated(version, replacement=None):
    '''
    Warns the user that something is deprecated until `version`.
    '''

    def wrapper(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            replace_resp = ""
            if replacement:
                replace_resp = (
                    " Please see {replacement} as a replacement for this "
                    "functionality.".format(replacement=replacement)
                )
            warnings.warn(
                "Function {name} is deprecated and will be removed in verison {target} "
                "(current version {current}).{replace_resp}".format(
                    name=func.__name__,
                    target=version,
                    current=pm_version,
                    replace_resp=replace_resp,
                ),
                category=DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return new_func

    return wrapper


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
