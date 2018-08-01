import os
import sys

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


def get_notebook_path(*args):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notebooks', *args)


def get_notebook_dir(*args):
    return os.path.dirname(get_notebook_path(*args))


class RedirectOutput(object):
    def __init__(self):
        self.redirected_stdout = None
        self.redirected_stderr = None
        self.old_stdout = None
        self.old_stderr = None

    def __enter__(self):
        self.old_stdout = sys.stdout
        sys.stdout = self.redirected_stdout = StringIO()
        self.old_stderr = sys.stderr
        sys.stderr = self.redirected_stderr = StringIO()
        return self

    def __exit__(self, *args):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr

    def get_stdout(self):
        return self.redirected_stdout.getvalue()

    def get_stderr(self):
        return self.redirected_stderr.getvalue()
