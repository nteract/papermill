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
