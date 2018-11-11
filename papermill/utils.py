import logging

from functools import wraps


logger = logging.getLogger('papermill.utils')


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
