"""Sets up a logger"""
import logging

logger = logging.getLogger('papermill')
notebook_logger = logging.getLogger('papermill.notebook')
"""
Logger for notebook output. Is automatically reconfigured on init to
not auto insert newline characters.
"""

class NbOutputStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # issue 35046: merged two stream.writes into one.
            stream.write(msg)
            self.flush()
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record) 

def _reconfigure_notebook_logger(l: logging.Logger):
    l.handlers = []
    custom_handler = NbOutputStreamHandler()
    l.addHandler(custom_handler)
    formatter = logging.Formatter('%(message)s')
    custom_handler.setFormatter(formatter)
    l.propagate = False

_reconfigure_notebook_logger(notebook_logger)

