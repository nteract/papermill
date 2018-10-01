from functools import wraps
import logging

logger = logging.getLogger('papermill.utils')


# retry decorator
def retry(num):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(num):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.debug('retrying: {}'.format(e))
            else:
                raise Exception  # TODO verify what to raise

        return wrapper

    return decorate
