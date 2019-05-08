import os
import logging

from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger('papermill.utils')

WARN_ON_ARGS_OVERWRITE = True

def safe_kwargs(caller_args, **callee_args):
    if WARN_ON_ARGS_OVERWRITE:
        conflicts = set(caller_args) & set(callee_args)
        if conflicts:
            args = format('; '.join(['{}={}'.format(key, value)
                                     for key, value in callee_args.items()]))
            msg = 'Callee will overwrite caller''s argument(s): {}'.format(args)
            warnings.warn(msg)
    return dict(caller_args, **callee_args)


def remove_args(args=None, kwargs=None):
    kwargs = kwargs if kwargs else {}
    if not args:
        return kwargs
    return dict([(key, kwargs.get(key)) for key in kwargs if key not in args])


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
